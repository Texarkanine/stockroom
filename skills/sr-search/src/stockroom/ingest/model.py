"""Harness-neutral intermediate records produced by the parsers.

These three dataclasses are the contract between the per-harness parsers and
the writer. A parser's only job is to turn a session file into a
:class:`NormalizedSession`; the writer's only job is to persist one. Neither
knows about the other, and the SQL schema is touched in exactly one place (the
writer).

The fields mirror the locked ``0001`` schema's *one meaning per column*
contract: where a harness genuinely lacks a grain (e.g. Cursor has no
per-message model or token usage), the corresponding field stays ``None`` — we
never fabricate a value. ``harness`` lives once on the session and the writer
denormalizes it onto every ``messages``/``tool_calls`` row.

Identity is positional and deterministic: a message's ``ordinal`` is its dense
0-based index over *kept* messages in conversation order, and ``parent_ordinal``
points at the ordinal of its parent message (``None`` for a root). The writer
expands these into the schema's ``message_id = '{session_id}#{ordinal}'`` and
the matching ``parent_id``; the native ids the harnesses carry are preserved
only as provenance (``source_uuid`` / ``source_tool_use_id``), never joined on.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class NormalizedToolCall:
    """A single ``tool_use`` block: stored as a ``tool_calls`` row (inputs only).

    ``ordinal`` is the block index of this ``tool_use`` within its message's
    content-block array (faithful to position relative to text). ``tool_input``
    is the whole, untruncated input object (the writer serializes it to JSON).
    ``source_tool_use_id`` is provenance (Claude's ``toolu_...`` id; ``None`` for
    Cursor, which emits no tool-use id) and is what a Claude subagent's
    ``spawning_tool_use_id`` joins back to.
    """

    ordinal: int
    tool_name: str
    tool_input: Any
    source_tool_use_id: str | None = None


@dataclass
class NormalizedMessage:
    """A kept conversation turn: one ``messages`` row plus its tool calls.

    ``ordinal`` is the dense 0-based index over kept messages in conversation
    order; ``parent_ordinal`` is the ordinal of the parent turn (``None`` at the
    root). The token/model/ts fields are populated only where the harness
    exposes them (Claude), and are honestly ``None`` otherwise (Cursor).
    """

    ordinal: int
    role: str
    parent_ordinal: int | None = None
    text: str | None = None
    model: str | None = None
    ts: datetime | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    cache_creation_tokens: int | None = None
    cache_read_tokens: int | None = None
    source_uuid: str | None = None
    tool_calls: list[NormalizedToolCall] = field(default_factory=list)


@dataclass
class NormalizedSession:
    """A whole conversation (or subagent run): one ``sessions`` row + messages.

    ``harness`` and ``session_id`` form the destination ``(harness, session_id)``
    primary-key grain; ``source_path`` is the absolute path to the ``.jsonl``
    (provenance + the watermark key), and ``source_mtime`` is that transcript's
    mtime at discovery as naive UTC (a durable, harness-uniform provenance
    time).     Workspace identity is three single-meaning fields: ``project_id`` is
    the harness's encoded project-dir slug stored *verbatim* (always present,
    the harness identity), ``cwd`` is the real project-root path — best-effort
    and honestly ``None`` when it cannot be recovered (never fabricated from
    the lossy slug), and ``workspace_key`` is an optional cross-harness rollup
    key derived at write from per-harness strategies (NULL when underivable).
    Subagent sessions set ``is_subagent`` and their parent-linkage fields
    (``parent_session_id`` and, for Claude, ``spawning_tool_use_id``).
    Grain-specific fields follow the schema's no-faking rule: ``models``
    (session-grain, Cursor via enrichment) vs each message's ``model``
    (Claude); session-grain ``*_tokens`` vs each message's ``*_tokens``
    (same dual-grain honesty — parsers fill only the grain the harness
    reports; never invent one from the other); ``started_at``/``ended_at``
    are Claude's min/max timestamps (naive UTC) and ``None`` for Cursor.
    """

    harness: str
    session_id: str
    source_path: str
    source_mtime: datetime | None = None
    is_subagent: bool = False
    project_id: str | None = None
    cwd: str | None = None
    workspace_key: str | None = None
    git_branch: str | None = None
    parent_session_id: str | None = None
    agent_id: str | None = None
    agent_type: str | None = None
    spawning_tool_use_id: str | None = None
    agent_name: str | None = None
    models: list[str] | None = None
    title: str | None = None
    harness_version: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    cache_creation_tokens: int | None = None
    cache_read_tokens: int | None = None
    messages: list[NormalizedMessage] = field(default_factory=list)
