"""Clean-room Cursor parser tests.

Cursor transcripts are metadata-sparse ``role``/``message`` JSONL with no native
ids, no per-turn wall-clock, and no per-message model. Identity is therefore
purely positional (dense 0-based ordinal over kept messages; linear
previous-kept parent). ``turn_ended`` markers are turn boundaries, not content,
and an empty ``text`` block ('') is kept (distinct from a turn with no text
channel). Tool-call ordinals are the block index of the ``tool_use`` within its
turn's content array — faithful to position relative to the text block.
"""

from pathlib import Path

from stockroom.ingest import cursor

_BASE = "home-user-project/agent-transcripts"


def _conv(cursor_root: Path, name: str) -> Path:
    return cursor_root / _BASE / name / f"{name}.jsonl"


def test_simple_conversation_dense_ordinals_linear_parents(cursor_root: Path) -> None:
    """A simple conversation yields ordered messages with dense ordinals and a
    linear previous-kept parent chain (root parent is None).
    """
    session = cursor.parse_session(_conv(cursor_root, "simple-conversation"))
    assert session.harness == "cursor"
    assert session.session_id == "simple-conversation"
    assert session.source_path.endswith("simple-conversation.jsonl")
    assert session.is_subagent is False
    # 4 kept messages (the trailing turn_ended is a boundary, not a message).
    ordinals = [m.ordinal for m in session.messages]
    roles = [m.role for m in session.messages]
    parents = [m.parent_ordinal for m in session.messages]
    assert ordinals == [0, 1, 2, 3]
    assert roles == ["user", "assistant", "assistant", "assistant"]
    assert parents == [None, 0, 1, 2]


def test_cursor_has_no_model_or_token_or_ts_grain(cursor_root: Path) -> None:
    """Cursor exposes no per-message model/tokens/timestamp — all honestly None."""
    session = cursor.parse_session(_conv(cursor_root, "simple-conversation"))
    m = session.messages[1]
    assert m.model is None
    assert m.ts is None
    assert m.input_tokens is None
    assert m.output_tokens is None
    assert m.cache_creation_tokens is None
    assert m.cache_read_tokens is None
    assert m.source_uuid is None
    # Session-grain wall-clock is absent too (do not fabricate).
    assert session.started_at is None
    assert session.ended_at is None
    assert session.models is None


def test_assistant_text_plus_tool_use_block_index_ordinal(cursor_root: Path) -> None:
    """An assistant turn keeps its text and emits a tool_call whose ordinal is
    the tool_use's block index; Cursor tool calls carry no source id.
    """
    session = cursor.parse_session(_conv(cursor_root, "simple-conversation"))
    turn = session.messages[1]
    assert turn.text == "I'll read the file first, then add the function."
    assert len(turn.tool_calls) == 1
    tc = turn.tool_calls[0]
    assert tc.tool_name == "Read"
    assert tc.ordinal == 1  # block index: [text(0), tool_use(1)]
    assert tc.tool_input == {"path": "src/utils.py"}
    assert tc.source_tool_use_id is None


def test_empty_text_block_is_kept_not_dropped(cursor_root: Path) -> None:
    """A turn whose only text block is '' keeps text == '' (turn not dropped)."""
    session = cursor.parse_session(_conv(cursor_root, "simple-conversation"))
    turn = session.messages[2]  # text:"" + StrReplace
    assert turn.text == ""
    assert turn.tool_calls[0].tool_name == "StrReplace"


def test_many_tools_distinct_block_index_ordinals(cursor_root: Path) -> None:
    """A single assistant turn with many tool_use blocks keeps empty text and
    assigns each tool call its distinct content-block-index ordinal.
    """
    session = cursor.parse_session(_conv(cursor_root, "pathological-many-tools"))
    # user(0), assistant-with-tools(1), assistant-summary(2)
    tools_turn = session.messages[1]
    assert tools_turn.text == ""
    names = [(tc.ordinal, tc.tool_name) for tc in tools_turn.tool_calls]
    assert names == [
        (1, "Glob"),
        (2, "Grep"),
        (3, "Read"),
        (4, "Read"),
        (5, "TodoWrite"),
    ]


def test_turn_ended_error_is_consumed_not_stored(cursor_root: Path) -> None:
    """A ``turn_ended`` (even status:error) produces no row; prior turns remain."""
    session = cursor.parse_session(_conv(cursor_root, "pathological-turn-ended-error"))
    assert [m.role for m in session.messages] == ["user", "assistant"]
    assert [m.ordinal for m in session.messages] == [0, 1]
    assert session.messages[1].tool_calls[0].tool_name == "Shell"


def test_subagent_session_identity_and_parent_linkage(cursor_root: Path) -> None:
    """A Cursor subagent file becomes its own session: is_subagent, parent
    linkage to the conversation dir, agent_id = file stem, agent_type from the
    parent's Task tool_use input, and a NULL spawning_tool_use_id (structural).
    """
    conv = "00000000-0000-4000-8000-000000000001"
    parent_path = _conv(cursor_root, conv)
    child_path = (
        parent_path.parent
        / "subagents"
        / ("00000000-0000-4000-8000-0000000000a1.jsonl")
    )
    parent = cursor.parse_session(parent_path)
    sub = cursor.parse_subagent(child_path, parent=parent)
    assert sub.is_subagent is True
    assert sub.session_id == "00000000-0000-4000-8000-0000000000a1"
    assert sub.agent_id == "00000000-0000-4000-8000-0000000000a1"
    assert sub.parent_session_id == conv
    assert sub.agent_type == "explore"
    assert sub.spawning_tool_use_id is None
    # The subagent has its own within-session ordinals/parents.
    assert [m.ordinal for m in sub.messages] == [0, 1, 2]
    assert [m.parent_ordinal for m in sub.messages] == [None, 0, 1]
