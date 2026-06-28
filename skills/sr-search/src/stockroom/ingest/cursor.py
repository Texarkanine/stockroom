"""Clean-room parser for Cursor's native on-disk transcript format.

Reverse-engineered from the harness's own files (no reference to any
third-party tool). A Cursor conversation lives at
``<project>/agent-transcripts/<conv>/<conv>.jsonl`` — one JSON record per line,
each a ``{"role": ..., "message": {"content": [blocks]}}`` turn, with a
trailing ``{"role": "turn_ended", ...}`` boundary marker. Records are
metadata-sparse: no native message ids, no per-message model, no per-turn
timestamps, no token usage. Identity is therefore derived positionally.

Parsing rules (the milestone-1 schema contract, Cursor side):

* Kept turns are ``role == "user"`` and ``role == "assistant"``. Each gets a
  dense 0-based ``ordinal`` in file order; ``parent_ordinal`` is the previous
  kept turn (linear append), ``None`` at ordinal 0.
* ``turn_ended`` is consumed as a boundary and stored nowhere (there is no
  schema column for it in v1).
* A turn's ``text`` is its text block(s) joined in order, kept whole — including
  an empty ``''`` block. A turn with no text block at all has ``text = None``.
* Each ``tool_use`` block becomes a tool call whose ``ordinal`` is the block's
  index within the turn's content array (faithful to its position relative to
  the text). Cursor emits no tool-use id, so ``source_tool_use_id`` is ``None``.

This module depends only on :mod:`stockroom.ingest.model` and the stdlib — it
performs no I/O beyond reading the file handed to it, so it is pure and
unit-testable. ``project_id`` and ``cwd`` are not in the file: the orchestrator
stamps ``project_id`` (the verbatim project-dir slug from discovery) and
resolves ``cwd`` by re-encode-and-match over in-band paths
(:mod:`stockroom.ingest.paths`); both are left unset here.
"""

import json
from pathlib import Path

from stockroom.ingest.model import (
    NormalizedMessage,
    NormalizedSession,
    NormalizedToolCall,
)

#: Roles that become ``messages`` rows. Anything else (``turn_ended`` markers,
#: unknown future roles) is consumed without producing a row.
_MESSAGE_ROLES = {"user", "assistant"}


def _iter_records(path: Path) -> list[dict]:
    """Parse a ``.jsonl`` file into records, skipping blank/corrupt lines.

    Robustness over strictness: a truncated or malformed line (e.g. an
    interrupted write at the tail of a live file) is skipped rather than
    aborting the whole session.
    """
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


def _turn_text(content: list) -> str | None:
    """Join a turn's text blocks in order, or ``None`` if it has no text block.

    Distinguishes a turn with an empty text block (``''`` — kept) from a turn
    with no text channel at all (``None``), preserving the schema's
    empty-string-is-not-NULL contract.
    """
    texts = [
        block.get("text", "")
        for block in content
        if isinstance(block, dict) and block.get("type") == "text"
    ]
    if not texts:
        return None
    return "".join(texts)


def _turn_tool_calls(content: list) -> list[NormalizedToolCall]:
    """Build tool calls from a turn's ``tool_use`` blocks, keyed by block index."""
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


def _parse_messages(records: list[dict]) -> list[NormalizedMessage]:
    """Turn the raw records into kept messages with dense ordinals + parents."""
    messages: list[NormalizedMessage] = []
    prev_ordinal: int | None = None
    ordinal = 0
    for record in records:
        if record.get("role") not in _MESSAGE_ROLES:
            continue  # turn_ended boundary / unknown role: consumed, not stored
        content = record.get("message", {}).get("content", [])
        if not isinstance(content, list):
            content = []
        messages.append(
            NormalizedMessage(
                ordinal=ordinal,
                role=record["role"],
                parent_ordinal=prev_ordinal,
                text=_turn_text(content),
                tool_calls=_turn_tool_calls(content),
            )
        )
        prev_ordinal = ordinal
        ordinal += 1
    return messages


def parse_session(path: Path) -> NormalizedSession:
    """Parse a Cursor conversation ``.jsonl`` into a :class:`NormalizedSession`.

    The session id is the file stem (which equals the conversation directory
    name on disk). Subagent and grain-specific fields stay at their honest
    defaults: Cursor has no per-message model/tokens/timestamps and no
    session-grain wall-clock, and ``models`` is filled later (optionally) by
    enrichment.
    """
    path = Path(path)
    messages = _parse_messages(_iter_records(path))
    return NormalizedSession(
        harness="cursor",
        session_id=path.stem,
        source_path=str(path),
        messages=messages,
    )


def _parent_subagent_types(parent: NormalizedSession) -> list[str]:
    """Collect the ``subagent_type`` of each ``Task`` tool call in the parent.

    Cursor provides no id linking a ``Task`` tool_use to the child transcript,
    so linkage is structural (the child file lives in the parent's
    ``subagents/`` dir). The ``subagent_type`` is recovered positionally from
    the parent's ``Task`` inputs — best-effort, sufficient for the common
    single-subagent case.
    """
    types: list[str] = []
    for message in parent.messages:
        for call in message.tool_calls:
            if call.tool_name == "Task" and isinstance(call.tool_input, dict):
                subagent_type = call.tool_input.get("subagent_type")
                if subagent_type is not None:
                    types.append(subagent_type)
    return types


def parse_subagent(
    path: Path,
    *,
    parent: NormalizedSession,
    index: int = 0,
) -> NormalizedSession:
    """Parse a Cursor subagent ``.jsonl`` into a subagent :class:`NormalizedSession`.

    The subagent is its own session at the ``(harness, session_id)`` grain with
    its own within-session ordinals/parents. Identity and linkage:

    * ``session_id`` / ``agent_id`` = the child file stem,
    * ``parent_session_id`` = the parent conversation id (the conv directory two
      levels up: ``<conv>/subagents/<child>.jsonl``),
    * ``agent_type`` = the ``index``-th ``Task.subagent_type`` from the parent
      (positional best-effort; ``None`` if unavailable),
    * ``spawning_tool_use_id`` = ``None`` (Cursor emits no tool-use id — the
      link is purely structural).
    """
    path = Path(path)
    messages = _parse_messages(_iter_records(path))
    subagent_types = _parent_subagent_types(parent)
    agent_type = subagent_types[index] if index < len(subagent_types) else None
    return NormalizedSession(
        harness="cursor",
        session_id=path.stem,
        source_path=str(path),
        is_subagent=True,
        parent_session_id=path.parent.parent.name,
        agent_id=path.stem,
        agent_type=agent_type,
        spawning_tool_use_id=None,
        messages=messages,
    )
