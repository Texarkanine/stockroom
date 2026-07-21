"""Clean-room parser for Cursor Agent CLI ``store.db`` chats.

CLI chats live at ``~/.cursor/chats/<project-hash>/<agentId>/store.db`` — a
SQLite DB with ``meta`` (hex-encoded JSON) and ``blobs(id, data)``. Conversation
order comes from an ordered root-hash walk of ``latestRootBlobId`` (repeated
protobuf length-delimited 32-byte refs); JSON ``user``/``assistant`` leaves
become warehouse messages. See
``memory-bank/active/creative/creative-cursor-cli-store-parse.md``.

Parsing rules:

* ``session_id`` / ``agent_id`` = parent directory name (equals ``meta.agentId``)
* ``entrypoint`` = ``cli`` (synthesized from provenance)
* ``title`` = ``meta.name`` when present; ``models`` = ``[lastUsedModel]`` when set
* ``started_at`` = ``createdAt`` milliseconds → naive UTC
* ``cwd`` = best-effort ``Workspace Path:`` from the first user_info text
* Kept turns: JSON leaves with ``role`` in ``{user, assistant}``
* Drop ``system``, ``tool`` (tool-result), non-JSON / corrupt leaves
* Content parts: ``text`` kept; ``tool-call`` → tool call; ``reasoning`` dropped
* Dense ordinals over kept turns; linear ``parent_ordinal``

``project_id`` is the parent hash directory and is stamped by the orchestrator
from discovery (same pattern as the IDE parser).
"""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any

from stockroom.ingest.model import (
    NormalizedMessage,
    NormalizedSession,
    NormalizedToolCall,
)
from stockroom.timestamps import utc_from_timestamp

#: Roles that become ``messages`` rows.
_MESSAGE_ROLES = {"user", "assistant"}

#: Protobuf wire: field 1, wire type 2 (length-delimited) → tag byte ``0x0a``.
_ROOT_FIELD_TAG = 0x0A
_HASH_LEN = 32

_WORKSPACE_PATH_RE = re.compile(
    r"^Workspace Path:\s*(.+?)\s*$", re.MULTILINE
)


def _read_meta(con: sqlite3.Connection) -> dict[str, Any]:
    """Decode the hex-JSON ``meta`` row (key ``0``). Empty dict on failure."""
    row = con.execute("SELECT value FROM meta WHERE key = ?", ("0",)).fetchone()
    if row is None or row[0] is None:
        return {}
    raw = row[0]
    try:
        if isinstance(raw, bytes):
            text = raw.decode("utf-8")
        else:
            text = bytes.fromhex(str(raw)).decode("utf-8")
        obj = json.loads(text)
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
        return {}
    return obj if isinstance(obj, dict) else {}


def _load_blobs(con: sqlite3.Connection) -> dict[str, bytes]:
    """Load all blob id → data mappings."""
    return {
        str(bid): data
        for bid, data in con.execute("SELECT id, data FROM blobs")
        if bid is not None and data is not None
    }


def _root_blob_ids(root: bytes) -> list[str]:
    """Extract ordered 32-byte blob ids from a root blob.

    Scans for repeated ``0a 20 <sha256>`` length-delimited fields. Unknown
    framing bytes are skipped so a layout drift fails soft (empty / partial
    order) rather than aborting ingest.
    """
    ids: list[str] = []
    i = 0
    n = len(root)
    while i < n:
        if (
            root[i] == _ROOT_FIELD_TAG
            and i + 1 < n
            and root[i + 1] == _HASH_LEN
            and i + 2 + _HASH_LEN <= n
        ):
            ids.append(root[i + 2 : i + 2 + _HASH_LEN].hex())
            i += 2 + _HASH_LEN
        else:
            i += 1
    return ids


def _decode_leaf(data: bytes) -> dict[str, Any] | None:
    """Parse a blob as a JSON object, or ``None`` if corrupt / non-object."""
    try:
        obj = json.loads(data)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    return obj if isinstance(obj, dict) else None


def _normalize_content(content: Any) -> list:
    """Normalize a leaf's ``content`` to a list of blocks.

    String content becomes a single synthetic text block so user_info-style
    leaves share the same extraction path as structured turns.
    """
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    if isinstance(content, list):
        return content
    return []


def _turn_text(content: list) -> str | None:
    """Join text blocks in order; ``None`` when no text channel exists."""
    texts = [
        block.get("text", "")
        for block in content
        if isinstance(block, dict) and block.get("type") == "text"
    ]
    if not texts:
        return None
    return "".join(texts)


def _turn_tool_calls(content: list) -> list[NormalizedToolCall]:
    """Build tool calls from ``tool-call`` parts, keyed by block index."""
    calls: list[NormalizedToolCall] = []
    for index, block in enumerate(content):
        if not isinstance(block, dict) or block.get("type") != "tool-call":
            continue
        calls.append(
            NormalizedToolCall(
                ordinal=index,
                tool_name=block.get("toolName") or "",
                tool_input=block.get("args", {}),
                source_tool_use_id=block.get("toolCallId"),
            )
        )
    return calls


def _cwd_from_text(text: str | None) -> str | None:
    """Extract ``Workspace Path:`` from user_info text when present."""
    if not text:
        return None
    match = _WORKSPACE_PATH_RE.search(text)
    if match is None:
        return None
    path = match.group(1).strip()
    return path or None


def _parse_messages(
    ordered_ids: list[str], blobs: dict[str, bytes]
) -> tuple[list[NormalizedMessage], str | None]:
    """Walk root order into kept messages; recover cwd from the first user_info."""
    messages: list[NormalizedMessage] = []
    cwd: str | None = None
    prev_ordinal: int | None = None
    ordinal = 0
    for blob_id in ordered_ids:
        data = blobs.get(blob_id)
        if data is None:
            continue
        leaf = _decode_leaf(data)
        if leaf is None:
            continue
        role = leaf.get("role")
        if role not in _MESSAGE_ROLES:
            continue
        content = _normalize_content(leaf.get("content"))
        text = _turn_text(content)
        if cwd is None and role == "user":
            cwd = _cwd_from_text(text)
        messages.append(
            NormalizedMessage(
                ordinal=ordinal,
                role=role,
                parent_ordinal=prev_ordinal,
                text=text,
                tool_calls=_turn_tool_calls(content),
            )
        )
        prev_ordinal = ordinal
        ordinal += 1
    return messages, cwd


def parse_session(path: Path) -> NormalizedSession:
    """Parse a Cursor Agent CLI ``store.db`` into a :class:`NormalizedSession`.

    ``session_id`` / ``agent_id`` are the parent directory name (``meta.agentId``).
    ``entrypoint`` is synthesized as ``cli``. Kept turns are JSON ``user`` /
    ``assistant`` leaves in root order; ``system``, ``tool``, reasoning parts,
    and non-JSON leaves are skipped.
    """
    path = Path(path)
    session_id = path.parent.name
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        meta = _read_meta(con)
        blobs = _load_blobs(con)
    finally:
        con.close()

    root_id = meta.get("latestRootBlobId")
    ordered_ids: list[str] = []
    if isinstance(root_id, str) and root_id in blobs:
        ordered_ids = _root_blob_ids(blobs[root_id])

    messages, cwd = _parse_messages(ordered_ids, blobs)

    started_at = None
    created_at = meta.get("createdAt")
    if isinstance(created_at, (int, float)):
        started_at = utc_from_timestamp(created_at / 1000.0)

    models = None
    last_model = meta.get("lastUsedModel")
    if isinstance(last_model, str) and last_model:
        models = [last_model]

    title = meta.get("name")
    if title is not None and not isinstance(title, str):
        title = None

    agent_id = meta.get("agentId")
    if not isinstance(agent_id, str) or not agent_id:
        agent_id = session_id

    return NormalizedSession(
        harness="cursor",
        session_id=session_id,
        source_path=str(path),
        agent_id=agent_id,
        title=title,
        models=models,
        started_at=started_at,
        cwd=cwd,
        entrypoint="cli",
        messages=messages,
    )
