"""Parser for Claude Code's native on-disk transcript format.

A Claude session lives at ``<project>/<sessionId>.jsonl`` —
one self-describing JSON record per line. Records carry a native ``uuid`` and
``parentUuid`` (a tree that genuinely *branches*), a ``type`` drawn from a large
set, and — for assistant turns — ``message.model``, ``message.usage`` token
counts, and a ``message.content`` block array.

Parsing rules (the milestone-1 schema contract, Claude side):

* Kept records become ``messages``: ``assistant`` turns always, and ``user``
  turns that carry real text (a ``content`` string, or a ``content`` list with
  at least one ``text`` block). A ``user`` record whose content is only
  ``tool_result`` is a tool *output* and is dropped (inputs only).
* Within an assistant turn, ``thinking`` blocks are dropped (only ``text`` is
  kept), and each ``tool_use`` block becomes a tool call keyed by its block
  index; the native ``toolu_...`` id is preserved as provenance.
* Metadata records fold into the session: ``ai-title``/``custom-title`` ->
  ``title`` (custom wins), ``agent-name`` -> ``agent_name``. The many remaining
  non-content types (``system``, ``attachment``, ``file-history-snapshot``,
  ``permission-mode``, ``last-prompt``, ``queue-operation``, ``mode``, ...) are
  ignored without producing rows.
* Identity is the dense 0-based ordinal over kept messages; ``parent_ordinal``
  is found by walking this record's ``parentUuid`` up the (uuid -> parentUuid)
  chain — past any dropped records — to the nearest *kept* ancestor. The native
  ``uuid`` is preserved only as ``source_uuid`` provenance, never joined on.
* Token counts are once per API response, not once per content-block line.
  Assistant lines that share a non-empty ``message.id`` and ``requestId`` are
  one response: the field-wise max of the four counts stays on the last of
  those lines, and the other lines in the group store ``NULL``. A line missing
  either id keeps its own usage. Those two ids are not persisted. Rows whose
  transcripts are already gone stay as stored: without the transcript, a
  later pass cannot tell a repeated response from two responses that share a
  cache triple. A user row or a time gap between those lines also occurs
  inside one response, and is not a repair.

This module depends only on :mod:`stockroom.ingest.model` and the stdlib.
"""

import json
from datetime import datetime
from pathlib import Path

from stockroom.ingest.model import (
    NormalizedMessage,
    NormalizedSession,
    NormalizedToolCall,
)
from stockroom.timestamps import to_utc_naive


def _iter_records(path: Path) -> list[dict]:
    """Parse a ``.jsonl`` file into records, skipping blank/corrupt lines."""
    records: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            records.append(obj)
    return records


def _parse_ts(value: object) -> datetime | None:
    """Parse an ISO-8601 timestamp (``...Z`` accepted) to a naive-UTC datetime.

    DuckDB's ``TIMESTAMP`` is timezone-naive; stockroom stores UTC wall clock.
    Aware stamps (including trailing ``Z``) are converted to UTC before tzinfo
    is dropped.
    """
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return to_utc_naive(parsed)


def _user_text(content: object) -> str | None:
    """Return a user turn's text, or ``None`` if it carries none.

    A string content is the text verbatim. A list content contributes its
    ``text`` blocks (joined); a list with no text block (e.g. only
    ``tool_result``) yields ``None`` — the caller treats that as a dropped turn.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        texts = [
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        ]
        if texts:
            return "\n".join(texts)
    return None


def _assistant_text(content: object) -> str | None:
    """Join an assistant turn's ``text`` blocks (thinking/tool_use ignored)."""
    if not isinstance(content, list):
        return None
    texts = [
        block.get("text", "")
        for block in content
        if isinstance(block, dict) and block.get("type") == "text"
    ]
    if not texts:
        return None
    return "\n".join(texts)


def _assistant_tool_calls(content: object) -> list[NormalizedToolCall]:
    """Build tool calls from an assistant turn's ``tool_use`` blocks."""
    if not isinstance(content, list):
        return []
    calls: list[NormalizedToolCall] = []
    for index, block in enumerate(content):
        if not isinstance(block, dict) or block.get("type") != "tool_use":
            continue
        calls.append(
            NormalizedToolCall(
                ordinal=index,
                tool_name=block.get("name", ""),
                tool_input=block.get("input", {}),
                source_tool_use_id=block.get("id"),
            )
        )
    return calls


def _is_kept(record: dict) -> bool:
    """True if a record becomes a ``messages`` row.

    Assistant turns are always kept; user turns are kept only when they carry
    real text (so inputs-only ``tool_result`` user records are dropped).
    """
    record_type = record.get("type")
    if record_type == "assistant":
        return True
    if record_type == "user":
        return _user_text(record.get("message", {}).get("content")) is not None
    return False


def _resolve_parent(
    parent_uuid: object,
    parent_of: dict,
    kept_ordinal: dict,
) -> int | None:
    """Walk ``parentUuid`` to the nearest kept ancestor's ordinal (else None).

    Steps from ``parent_uuid`` up the (uuid -> parentUuid) chain, skipping
    dropped records, until it lands on a uuid that belongs to a kept message.
    A ``seen`` guard makes a malformed cycle terminate instead of hanging.
    """
    cursor = parent_uuid
    seen: set = set()
    while isinstance(cursor, str) and cursor not in seen:
        if cursor in kept_ordinal:
            return kept_ordinal[cursor]
        seen.add(cursor)
        cursor = parent_of.get(cursor)
    return None


def _build_message(
    record: dict, ordinal: int, parent_ordinal: int | None
) -> NormalizedMessage:
    """Turn a kept record into a :class:`NormalizedMessage`."""
    message = record.get("message", {})
    ts = _parse_ts(record.get("timestamp"))
    uuid = record.get("uuid")
    if record.get("type") == "user":
        return NormalizedMessage(
            ordinal=ordinal,
            role="user",
            parent_ordinal=parent_ordinal,
            text=_user_text(message.get("content")),
            ts=ts,
            source_uuid=uuid,
        )
    usage = message.get("usage", {}) or {}
    content = message.get("content", [])
    raw_id = message.get("id")
    raw_request = record.get("requestId")
    return NormalizedMessage(
        ordinal=ordinal,
        role="assistant",
        parent_ordinal=parent_ordinal,
        text=_assistant_text(content),
        model=message.get("model"),
        ts=ts,
        input_tokens=usage.get("input_tokens"),
        output_tokens=usage.get("output_tokens"),
        cache_creation_tokens=usage.get("cache_creation_input_tokens"),
        cache_read_tokens=usage.get("cache_read_input_tokens"),
        source_uuid=uuid,
        api_message_id=raw_id if isinstance(raw_id, str) and raw_id else None,
        request_id=raw_request
        if isinstance(raw_request, str) and raw_request
        else None,
        tool_calls=_assistant_tool_calls(content),
    )


_TOKEN_FIELDS = (
    "input_tokens",
    "output_tokens",
    "cache_creation_tokens",
    "cache_read_tokens",
)


def _response_key(record: dict) -> tuple[str, str] | None:
    """Return ``(message.id, requestId)`` when both are non-empty strings."""
    message = record.get("message")
    if not isinstance(message, dict):
        return None
    message_id = message.get("id")
    request_id = record.get("requestId")
    if (
        isinstance(message_id, str)
        and message_id
        and isinstance(request_id, str)
        and request_id
    ):
        return (message_id, request_id)
    return None


def _token_int(value: object) -> int | None:
    """Return ``value`` when it is an int token count, else ``None``.

    ``bool`` is an ``int`` subclass and is not a token count.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _attribute_response_usage(
    messages: list[NormalizedMessage],
    keys: list[tuple[str, str] | None],
) -> None:
    """Attribute each API response's token counts onto one kept line.

    ``keys`` aligns with ``messages``. A non-``None`` key is
    ``(message.id, requestId)``. Lines that share a key are one response:
    the field-wise max of the four token counts stays on the last of those
    lines, and the other lines in the group have their token columns cleared.
    A ``None`` key is not grouped; that line keeps whatever usage it carried.
    Non-int counts are ignored when computing the max.
    """
    groups: dict[tuple[str, str], list[int]] = {}
    for index, key in enumerate(keys):
        if key is None:
            continue
        groups.setdefault(key, []).append(index)
    for indexes in groups.values():
        if len(indexes) < 2:
            continue
        maxes: dict[str, int | None] = {}
        for field_name in _TOKEN_FIELDS:
            present = [
                counted
                for index in indexes
                if (counted := _token_int(getattr(messages[index], field_name)))
                is not None
            ]
            maxes[field_name] = max(present) if present else None
        for index in indexes:
            for field_name in _TOKEN_FIELDS:
                setattr(messages[index], field_name, None)
        winner = indexes[-1]
        for field_name, value in maxes.items():
            setattr(messages[winner], field_name, value)


def drop_copied_parent_usage(
    parent: NormalizedSession,
    subagents: list[NormalizedSession],
) -> None:
    """Clear token columns on subagent rows that repeat a parent API response.

    A forked subagent transcript can repeat the parent's ``(message.id,
    requestId)``. Those counts already live on the parent. Matching subagent
    rows have their four token fields cleared. The subagent's own responses,
    text, and tool calls stay. The parent is not modified.
    """
    parent_keys = {
        (message.api_message_id, message.request_id)
        for message in parent.messages
        if message.api_message_id and message.request_id
    }
    for subagent in subagents:
        for message in subagent.messages:
            key = (message.api_message_id, message.request_id)
            if key not in parent_keys:
                continue
            message.input_tokens = None
            message.output_tokens = None
            message.cache_creation_tokens = None
            message.cache_read_tokens = None


def _parse_messages(records: list[dict]) -> list[NormalizedMessage]:
    """Reconstruct kept messages with dense ordinals and tree-resolved parents."""
    parent_of: dict = {}
    for record in records:
        uuid = record.get("uuid")
        if isinstance(uuid, str):
            parent_of[uuid] = record.get("parentUuid")

    kept: list[tuple[dict, int]] = []
    kept_ordinal: dict = {}
    ordinal = 0
    for record in records:
        if not _is_kept(record):
            continue
        kept.append((record, ordinal))
        uuid = record.get("uuid")
        if isinstance(uuid, str):
            kept_ordinal[uuid] = ordinal
        ordinal += 1

    messages: list[NormalizedMessage] = []
    keys: list[tuple[str, str] | None] = []
    for record, ordn in kept:
        parent_ordinal = _resolve_parent(
            record.get("parentUuid"), parent_of, kept_ordinal
        )
        messages.append(_build_message(record, ordn, parent_ordinal))
        if record.get("type") == "assistant":
            keys.append(_response_key(record))
        else:
            keys.append(None)
    _attribute_response_usage(messages, keys)
    return messages


def _fold_metadata(records: list[dict]) -> dict:
    """Collect session-level fields scattered across the record stream.

    Title prefers a user-set ``custom-title`` over the generated ``ai-title``.
    The first-seen ``cwd``/``gitBranch``/``version``/``sessionId``/``agentId``/
    ``entrypoint`` wins (they are stable within a session).
    """
    info: dict = {}
    for record in records:
        record_type = record.get("type")
        if record_type == "ai-title":
            info.setdefault("ai_title", record.get("aiTitle"))
        elif record_type == "custom-title":
            info["custom_title"] = record.get("customTitle")
        elif record_type == "agent-name":
            info["agent_name"] = record.get("agentName")
        for record_key, info_key in (
            ("cwd", "cwd"),
            ("gitBranch", "git_branch"),
            ("version", "version"),
            ("sessionId", "session_id"),
            ("agentId", "agent_id"),
            ("entrypoint", "entrypoint"),
        ):
            if record_key in record and info.get(info_key) is None:
                info[info_key] = record.get(record_key)
    return info


def _time_span(
    messages: list[NormalizedMessage],
) -> tuple[datetime | None, datetime | None]:
    """Return (min, max) of the kept messages' timestamps, or (None, None)."""
    stamps = [m.ts for m in messages if m.ts is not None]
    if not stamps:
        return None, None
    return min(stamps), max(stamps)


def _title(meta: dict) -> str | None:
    """A user-set custom title wins over the generated ai-title."""
    return meta.get("custom_title") or meta.get("ai_title")


def parse_session(path: Path) -> NormalizedSession:
    """Parse a Claude conversation ``.jsonl`` into a :class:`NormalizedSession`.

    The session id is the ``sessionId`` carried by the records (falling back to
    the file stem). ``models`` stays ``None`` — Claude's model grain is
    per-message, not per-session. ``project_id`` (the verbatim project-dir slug)
    is stamped by the orchestrator from discovery; the authoritative ``cwd`` here
    comes straight from the records.
    """
    path = Path(path)
    records = _iter_records(path)
    messages = _parse_messages(records)
    meta = _fold_metadata(records)
    started_at, ended_at = _time_span(messages)
    return NormalizedSession(
        harness="claude",
        session_id=meta.get("session_id") or path.stem,
        source_path=str(path),
        cwd=meta.get("cwd"),
        git_branch=meta.get("git_branch"),
        title=_title(meta),
        agent_name=meta.get("agent_name"),
        harness_version=meta.get("version"),
        started_at=started_at,
        ended_at=ended_at,
        entrypoint=meta.get("entrypoint"),
        messages=messages,
    )


def _read_meta(meta_path: Path | None) -> dict:
    """Read a subagent ``.meta.json`` (``{agentType, description, toolUseId}``)."""
    if meta_path is None:
        return {}
    meta_path = Path(meta_path)
    if not meta_path.is_file():
        return {}
    try:
        obj = json.loads(meta_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def parse_subagent(
    path: Path,
    *,
    meta_path: Path | None = None,
) -> NormalizedSession:
    """Parse a Claude subagent ``.jsonl`` into a subagent :class:`NormalizedSession`.

    Critically, the subagent's ``session_id`` is the **file stem** (e.g.
    ``agent-aaa111``), *not* the ``sessionId`` its records carry — that field
    holds the *parent's* session id on disk and is used as
    ``parent_session_id``. The spawn linkage comes from the sibling
    ``.meta.json``: ``agentType`` -> ``agent_type`` and ``toolUseId`` ->
    ``spawning_tool_use_id`` (which joins the parent's ``Task`` tool-call
    provenance id). ``agent_id`` and ``agent_name`` come from the subagent's own
    records.
    """
    path = Path(path)
    records = _iter_records(path)
    messages = _parse_messages(records)
    meta = _fold_metadata(records)
    agent_meta = _read_meta(meta_path)
    started_at, ended_at = _time_span(messages)
    return NormalizedSession(
        harness="claude",
        session_id=path.stem,
        source_path=str(path),
        is_subagent=True,
        parent_session_id=meta.get("session_id"),
        cwd=meta.get("cwd"),
        git_branch=meta.get("git_branch"),
        agent_id=meta.get("agent_id"),
        agent_type=agent_meta.get("agentType"),
        spawning_tool_use_id=agent_meta.get("toolUseId"),
        agent_name=meta.get("agent_name"),
        title=_title(meta),
        harness_version=meta.get("version"),
        started_at=started_at,
        ended_at=ended_at,
        entrypoint=meta.get("entrypoint"),
        messages=messages,
    )
