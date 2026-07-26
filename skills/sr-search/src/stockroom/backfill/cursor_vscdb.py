"""Clean-room parser for Cursor's legacy ``globalStorage/state.vscdb`` composers.

Cursor's IDE "composer" conversations live in a single multi-GB SQLite store
that nightly ingest never reads. Three shapes matter:

``cursorDiskKV(key TEXT UNIQUE, value BLOB)``
    ``composerData:{composerId}`` — ``name``, ``createdAt`` (epoch ms),
    ``modelConfig.modelName``, and an ordered ``fullConversationHeadersOnly``
    of ``{bubbleId, type}``. Older composers instead carry whole bubbles inline
    in a legacy ``conversation`` array. ``bubbleId:{composerId}:{bubbleId}`` —
    one turn: ``type`` (1 = user, 2 = assistant), ``text``, optional
    ``toolFormerData`` (a single tool call, or a husk carrying nothing but
    ``additionalData.status == "error"`` — 14% of them), optional ``thinking``,
    ``tokenCount``, a sparse ``modelInfo.modelName``, and usually an ISO-8601
    ``createdAt``.
``composerHeaders(composerId, workspaceId, …)``
    The workspace a composer belongs to.
``../workspaceStorage/{workspaceId}/workspace.json``
    ``{"folder": "<uri>"}`` for a single-root workspace; ``{"workspace": …}``
    for a multi-root one (no single folder, so no ``cwd``).

Two creative decisions govern the reconstruction, and both have full rationale
in the memory bank:

* ``creative-vscdb-message-reconstruction.md`` — keep only *storable* bubbles
  (non-empty text or a *named* tool call). Thinking-only, empty, and
  failed-call-husk bubbles are dropped: thinking is never persisted, so such a
  row would be empty in every column. Tool bubbles stay their own message rather
  than being merged into the preceding assistant turn, because the source
  records no turn grouping.
* ``creative-vscdb-workspace-identity.md`` — ``project_id`` is the native
  ``workspaceId`` stored verbatim (the same hash-as-``project_id`` precedent the
  Cursor CLI chats parser set), ``cwd`` is resolved from ``workspace.json``, and
  ``workspace_key`` is left to the writer so vscdb sessions converge with
  same-``cwd`` transcript sessions.

Model attribution is the one grain this store reports *better* than nightly
ingest, which has no per-message model for Cursor at all and gets session
models only from the recent ai-code-tracking sidecar. Both grains are read
here: ``modelConfig.modelName`` as the conversation's selected model and each
bubble's ``modelInfo.modelName`` as that turn's.

Two measured read decisions (D1/D2 in ``tasks.md``) shape every query here: the
open ladder tries ``mode=ro`` and falls back to ``immutable=1`` (the only mode
that works on a WSL→Windows mount), and key lookups use index range bounds
rather than ``LIKE`` — 0.05 s versus 2.88 s per composer on that mount, because
SQLite will not use an index for ``LIKE`` under the default case-insensitive
setting.
"""

from __future__ import annotations

import json
import os
import sqlite3
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

from stockroom.backfill import BackfillError
from stockroom.config import load_settings
from stockroom.ingest.model import (
    NormalizedMessage,
    NormalizedSession,
    NormalizedToolCall,
)
from stockroom.timestamps import to_utc_naive, utc_from_timestamp

#: Registry key / ``--source`` value.
NAME = "cursor-vscdb"

#: Warehouse ``harness`` label for sessions this adapter authors.
HARNESS = "cursor"

#: Env var overriding where ``state.vscdb`` is read from.
STATE_VSCDB_ENV_VAR = "STOCKROOM_CURSOR_STATE_VSCDB"

#: Config key naming the same store, reported in the unresolvable error.
STATE_VSCDB_CONFIG_KEY = "[cursor].state_vscdb"

#: CLI flag naming the same store, reported in the unresolvable error.
STATE_VSCDB_FLAG = "--state-vscdb"

#: Range-bounded key read (D2). Never ``LIKE``: that forfeits the index.
_KV_RANGE_SQL = "SELECT key, value FROM cursorDiskKV WHERE key >= ? AND key < ?"

#: Key prefix for a composer's own record.
_COMPOSER_PREFIX = "composerData:"

#: Key prefix for a composer's bubbles: ``bubbleId:{composerId}:{bubbleId}``.
_BUBBLE_PREFIX = "bubbleId:"

#: Cursor's bubble ``type`` discriminator. Any other value is not a turn.
_ROLES = {1: "user", 2: "assistant"}

#: Folder-URI schemes whose path component is a real filesystem path. Anything
#: else (including a multi-root ``workspace`` pointer) yields an honest unknown.
_FOLDER_URI_SCHEMES = frozenset({"vscode-remote", "file"})


def _workspace_root(source: Path) -> Path:
    """The ``workspaceStorage`` sibling of the store's ``globalStorage`` dir."""
    return Path(source).parent.parent / "workspaceStorage"


#: The open ladder (D1), tried in order. See :func:`open_readonly`.
_OPEN_MODES = ("mode=ro", "immutable=1")


def _key_range(prefix: str) -> tuple[str, str]:
    """Return ``(low, high)`` half-open bounds selecting every key under ``prefix``.

    The upper bound is ``prefix`` with its last character incremented, so
    ``'bubbleId:{id}:'`` bounds against ``'bubbleId:{id};'``. This is what lets
    SQLite use the ``key`` index; ``LIKE`` would not (D2).
    """
    return prefix, prefix[:-1] + chr(ord(prefix[-1]) + 1)


def resolve_source(override: Path | None = None) -> Path:
    """Locate ``state.vscdb``: explicit override, then env var, then config key.

    No conventional default is discoverable on WSL→Windows, where the store
    lives on the Windows side, so an operator must name it. Raises
    :class:`BackfillError` naming all three inputs when none is set. A path that
    is set but absent or unreadable resolves fine here and fails at open time —
    "not configured" (which the orchestrator may skip) and "configured but
    broken" (always an error) are deliberately different outcomes.
    """
    if override is not None:
        return Path(override).expanduser()
    from_env = os.environ.get(STATE_VSCDB_ENV_VAR)
    if from_env:
        return Path(from_env).expanduser()
    from_config = load_settings().cursor_state_vscdb
    if from_config is not None:
        return from_config
    raise BackfillError(
        f"{NAME}: no Cursor state.vscdb configured — set it with "
        f"{STATE_VSCDB_FLAG}, the {STATE_VSCDB_ENV_VAR} environment variable, "
        f"or {STATE_VSCDB_CONFIG_KEY} in config.toml"
    )


def open_readonly(source: Path) -> sqlite3.Connection:
    """Open ``source`` strictly read-only, trying ``mode=ro`` then ``immutable=1``.

    ``mode=ro`` is correct where it works (local stores, WAL respected).
    ``immutable=1`` is the only mode that opens the store over a WSL→Windows
    mount, where WAL locking is unsupported; its caveat is that the ``-wal``
    tail is invisible, so the newest writes are not seen — harmless for a
    historical backfill. Raises :class:`BackfillError` when neither rung opens
    a readable store, so callers never see a bare ``sqlite3`` exception.
    """
    source = Path(source)
    if not source.is_file():
        raise BackfillError(
            f"{NAME}: no readable Cursor state.vscdb at {source} — "
            "check the path, or close Cursor and re-run"
        )
    last_error: Exception | None = None
    for mode in _OPEN_MODES:
        con: sqlite3.Connection | None = None
        try:
            # ``as_uri()`` percent-encodes ``?`` / ``#`` so they cannot steal
            # the SQLite URI query string that carries ``mode`` / ``immutable``.
            con = sqlite3.connect(f"{source.resolve().as_uri()}?{mode}", uri=True)
            # SQLite opens lazily, so the first real read is what proves the
            # rung: a mount that cannot do WAL locking fails here, not above.
            con.execute("SELECT count(*) FROM sqlite_master").fetchone()
            return con
        except sqlite3.Error as exc:
            last_error = exc
            if con is not None:
                con.close()
    raise BackfillError(
        f"{NAME}: could not read {source} as a Cursor state.vscdb "
        f"({last_error}) — close Cursor and re-run, or check the path"
    )


def candidates(source: Path) -> list[str]:
    """Enumerate every composer id in the store, cheaply and in key order.

    Reads only ``composerData:`` keys — not their values — so the orchestrator
    can subtract the skip set before paying for bubble reconstruction.
    """
    low, high = _key_range(_COMPOSER_PREFIX)
    con = open_readonly(source)
    try:
        try:
            rows = con.execute(
                "SELECT key FROM cursorDiskKV WHERE key >= ? AND key < ? ORDER BY key",
                (low, high),
            ).fetchall()
        except sqlite3.Error as exc:
            raise BackfillError(
                f"{NAME}: {source} does not look like a Cursor state.vscdb ({exc})"
            ) from exc
    finally:
        con.close()
    return [row[0][len(_COMPOSER_PREFIX) :] for row in rows]


def workspace_folder(workspace_root: Path, workspace_id: str) -> str | None:
    """Resolve a workspace's real folder path from its ``workspace.json``.

    Reads ``{workspace_root}/{workspace_id}/workspace.json`` — an authoritative
    record at a path derived from the store's own location, never a filesystem
    search. ``{"folder": "<uri>"}`` names a single root, which is decoded to a
    real path; ``vscode-remote://<authority>/<path>`` and ``file://<path>`` are
    the two live schemes.

    Returns ``None`` — never raises — for a multi-root ``{"workspace": …}``
    pointer (no single folder exists), an unknown scheme, or a missing or
    unparseable file. An entirely absent ``workspaceStorage`` directory is a
    plausible state on a machine where only ``globalStorage`` was copied, and
    degrades every session to ``cwd = None`` rather than failing the run.
    """
    try:
        raw = (Path(workspace_root) / workspace_id / "workspace.json").read_bytes()
    except OSError:
        return None
    record = _decode(raw)
    if record is None:
        return None
    folder = record.get("folder")
    if not isinstance(folder, str) or not folder:
        return None
    parsed = urlsplit(folder)
    if parsed.scheme not in _FOLDER_URI_SCHEMES:
        return None
    path = unquote(parsed.path)
    return path or None


def _decode(value: object) -> dict | None:
    """Parse a stored value as a JSON object, or ``None`` when corrupt."""
    if isinstance(value, bytes):
        try:
            value = value.decode("utf-8")
        except UnicodeDecodeError:
            return None
    if not isinstance(value, str):
        return None
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _parse_ts(value: object) -> datetime | None:
    """Parse a bubble's ISO-8601 ``createdAt`` (``…Z`` accepted) to naive UTC.

    Mirrors :func:`stockroom.ingest.claude._parse_ts`: DuckDB's ``TIMESTAMP`` is
    timezone-naive and stockroom stores UTC wall clock.
    """
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return to_utc_naive(parsed)


def _token(counts: object, key: str) -> int | None:
    """Read one allowlisted ``tokenCount`` field, mapping a zero fill to ``None``.

    Cursor stamps ``{"inputTokens": 0, "outputTokens": 0}`` on unmetered turns;
    storing ``0`` would assert the turn provably cost nothing.
    """
    if not isinstance(counts, dict):
        return None
    value = counts.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        return None
    return value


def _model_name(record: dict, key: str) -> str | None:
    """Read a ``{key: {"modelName": …}}`` model label, or ``None`` when absent.

    Serves both grains: ``composerData.modelConfig`` names the conversation's
    selected model, and a bubble's ``modelInfo`` names the model that produced
    that turn (Cursor stamps it where the model is set or changed, not on every
    bubble). The literal ``"default"`` is a value, not a gap — it is what the
    picker recorded, and the ai-code-tracking sidecar already writes it for
    ordinary ingest, so translating it here would make one conversation report
    differently depending on which pipeline authored it.
    """
    holder = record.get(key)
    if not isinstance(holder, dict):
        return None
    name = holder.get("modelName")
    return name if isinstance(name, str) and name else None


def _tool_input(tool_data: dict) -> Any:
    """Recover a tool call's whole input: parsed ``rawArgs``, else ``params``.

    Live bubbles use both shapes — some carry the JSON in ``rawArgs``, others
    leave it empty and carry it in ``params``. When neither parses, the raw
    string is stored whole rather than dropped.
    """
    unparsed: list[str] = []
    for key in ("rawArgs", "params"):
        value = tool_data.get(key)
        if isinstance(value, (dict, list)):
            return value
        if isinstance(value, str) and value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                unparsed.append(value)
    return unparsed[0] if unparsed else {}


def _tool_call(bubble: dict, *, has_text: bool) -> NormalizedToolCall | None:
    """Build the bubble's single tool call, or ``None`` when it carries none.

    ``ordinal`` is the block index within the message: ``1`` behind text
    (mirroring an agent-transcript ``[text, tool_use]`` turn), ``0`` when the
    bubble is tool-only. ``toolFormerData.result`` is deliberately never read —
    tool *results* are not stored at any grain.

    A usable ``name`` is what makes this a call at all. The store leaves a husk
    — ``toolFormerData`` whose only key is ``additionalData.status == "error"``
    — wherever a call failed to materialize, and a nameless call is
    unattributable to any tool, so both are declined rather than recorded under
    a blank name.
    """
    tool_data = bubble.get("toolFormerData")
    if not isinstance(tool_data, dict):
        return None
    name = tool_data.get("name")
    if not isinstance(name, str) or not name.strip():
        return None
    return NormalizedToolCall(
        ordinal=1 if has_text else 0,
        tool_name=name,
        tool_input=_tool_input(tool_data),
        source_tool_use_id=tool_data.get("toolCallId"),
    )


def _build_message(
    bubble: dict, ordinal: int, parent_ordinal: int | None
) -> NormalizedMessage | None:
    """Turn one bubble into a message, or ``None`` when it is not storable.

    The OQ1 keep predicate: a bubble becomes a message when it has non-empty
    text or a tool call. Thinking-only and empty bubbles are dropped — since
    ``thinking`` is never persisted, such a row would be empty in every column.
    An unknown ``type`` is not a conversation turn at all.
    """
    role = _ROLES.get(bubble.get("type"))
    if role is None:
        return None
    raw_text = bubble.get("text")
    text = raw_text if isinstance(raw_text, str) and raw_text.strip() else None
    call = _tool_call(bubble, has_text=text is not None)
    if text is None and call is None:
        return None
    counts = bubble.get("tokenCount")
    return NormalizedMessage(
        ordinal=ordinal,
        role=role,
        parent_ordinal=parent_ordinal,
        text=text,
        model=_model_name(bubble, "modelInfo"),
        ts=_parse_ts(bubble.get("createdAt")),
        input_tokens=_token(counts, "inputTokens"),
        output_tokens=_token(counts, "outputTokens"),
        source_uuid=bubble.get("bubbleId"),
        tool_calls=[call] if call is not None else [],
    )


def _ordered_bubbles(
    con: sqlite3.Connection, composer_id: str, composer: dict
) -> list[dict]:
    """Return the composer's bubbles in conversation order.

    Prefers ``fullConversationHeadersOnly``, reading every one of the composer's
    bubble rows in a single range-bounded query (D2) and then indexing into it,
    so a conversation costs one query rather than one per turn. Headers naming a
    bubble Cursor has since pruned are skipped. Older composers carry whole
    bubbles inline in ``conversation`` instead; those are already in order.
    """
    headers = composer.get("fullConversationHeadersOnly")
    if isinstance(headers, list) and headers:
        low, high = _key_range(f"{_BUBBLE_PREFIX}{composer_id}:")
        by_id: dict[str, dict] = {}
        for key, value in con.execute(_KV_RANGE_SQL, (low, high)):
            bubble = _decode(value)
            if bubble is not None:
                by_id[key.rsplit(":", 1)[-1]] = bubble
        ordered = []
        for header in headers:
            if not isinstance(header, dict):
                continue
            bubble = by_id.get(str(header.get("bubbleId")))
            if bubble is not None:
                ordered.append(bubble)
        return ordered

    inline = composer.get("conversation")
    if isinstance(inline, list):
        return [entry for entry in inline if isinstance(entry, dict)]
    return []


def _workspace_id(con: sqlite3.Connection, composer_id: str) -> str | None:
    """Look up the composer's native ``workspaceId``, or ``None`` when unfiled."""
    row = con.execute(
        "SELECT workspaceId FROM composerHeaders WHERE composerId = ?",
        (composer_id,),
    ).fetchone()
    if row is None or not isinstance(row[0], str) or not row[0]:
        return None
    return row[0]


def _parse_composer(
    con: sqlite3.Connection,
    source: Path,
    composer_id: str,
    cwd_cache: dict[str, str | None],
) -> NormalizedSession | None:
    """Reconstruct one composer into a session, or ``None`` when it has none.

    Bubble order comes from ``fullConversationHeadersOnly``, falling back to the
    legacy inline ``conversation`` array. Only *storable* bubbles become
    messages (OQ1); a composer with no storable bubbles — an empty draft, or one
    whose bubbles Cursor has since pruned — yields ``None`` so the orchestrator
    can count it as skipped rather than writing an empty session.

    ``cwd_cache`` memoizes ``workspaceId`` -> folder across the run: hundreds of
    composers map to well under a hundred distinct workspaces.
    """
    row = con.execute(
        "SELECT value FROM cursorDiskKV WHERE key = ?",
        (f"{_COMPOSER_PREFIX}{composer_id}",),
    ).fetchone()
    composer = _decode(row[0]) if row is not None else None
    if composer is None:
        return None

    messages: list[NormalizedMessage] = []
    # Collected from every bubble, including ones OQ1 drops: unlike a token
    # count, a model name is not a property of one turn that would become a
    # lie somewhere else. The session list only claims the conversation used it.
    seen_models: list[str] = []
    parent_ordinal: int | None = None
    for bubble in _ordered_bubbles(con, composer_id, composer):
        bubble_model = _model_name(bubble, "modelInfo")
        if bubble_model is not None:
            seen_models.append(bubble_model)
        message = _build_message(bubble, len(messages), parent_ordinal)
        if message is None:
            continue
        messages.append(message)
        parent_ordinal = message.ordinal
    if not messages:
        return None

    selected_model = _model_name(composer, "modelConfig")
    # Selected model first, then bubble order: the list reads as the run did.
    models = list(
        dict.fromkeys(
            ([selected_model] if selected_model is not None else []) + seen_models
        )
    )

    stamps = [message.ts for message in messages if message.ts is not None]
    started_at = min(stamps) if stamps else _composer_created_at(composer)

    workspace_id = _workspace_id(con, composer_id)
    cwd = None
    if workspace_id is not None:
        if workspace_id not in cwd_cache:
            cwd_cache[workspace_id] = workspace_folder(
                _workspace_root(source), workspace_id
            )
        cwd = cwd_cache[workspace_id]

    title = composer.get("name")
    return NormalizedSession(
        harness=HARNESS,
        session_id=composer_id,
        source_path=str(source),
        # D8: the vscdb is one shared store, so its file mtime is not this
        # composer's activity time. The writer seeds first_seen_at from the run
        # clock instead of a fabricated one.
        source_mtime=None,
        project_id=workspace_id,
        cwd=cwd,
        models=models or None,
        # workspace_key is deliberately unset: the writer derives it from cwd,
        # which is what makes a vscdb session converge with the same-cwd
        # sessions ordinary ingest authored.
        title=title if isinstance(title, str) and title else None,
        started_at=started_at,
        ended_at=max(stamps) if stamps else None,
        entrypoint="ide",
        messages=messages,
    )


def _composer_created_at(composer: dict) -> datetime | None:
    """Convert ``composerData.createdAt`` (epoch milliseconds) to naive UTC."""
    created_at = composer.get("createdAt")
    if not isinstance(created_at, (int, float)) or isinstance(created_at, bool):
        return None
    return utc_from_timestamp(created_at / 1000.0)


def parse_all(source: Path, ids: list[str]) -> Iterator[NormalizedSession]:
    """Reconstruct the requested composers, yielding one session each.

    Composers that reconstruct to no messages (empty drafts — 273 of 908 on the
    probing machine) are skipped rather than yielded, and a composer whose rows
    are corrupt is skipped without aborting the run.
    """
    con = open_readonly(source)
    cwd_cache: dict[str, str | None] = {}
    try:
        for composer_id in ids:
            try:
                session = _parse_composer(con, source, composer_id, cwd_cache)
            except sqlite3.Error:
                continue
            if session is not None:
                yield session
    finally:
        con.close()
