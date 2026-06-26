"""Clean-room Claude Code parser tests.

Claude transcripts are self-describing JSONL with a native ``uuid``/``parentUuid``
tree, per-message ``model`` and token ``usage``, per-record timestamps, and a
zoo of record ``type``s. The parser must: keep only ``user`` (with real text)
and ``assistant`` turns; drop ``thinking`` blocks and ``tool_result`` outputs
(inputs only); fold metadata records (``ai-title``/``custom-title`` -> title,
``agent-name`` -> agent_name) into the session; ignore the many non-content
record types real logs emit; and reconstruct parents by walking the
``parentUuid`` tree to the nearest *kept* ancestor (the tree branches, so
positional linking would be wrong). Subagents are their own sessions whose id
is the file stem (records carry the *parent's* sessionId).
"""

import json
from pathlib import Path

from stockroom.ingest import claude

_BASE = "-home-user-project"


def _sess(claude_root: Path, name: str) -> Path:
    return claude_root / _BASE / f"{name}.jsonl"


def test_simple_conversation_thinking_dropped_tool_use_kept(claude_root: Path) -> None:
    """A simple conversation keeps user(str) + assistant turns, drops the
    ``thinking`` block (text only), and turns ``tool_use`` into a tool call with
    its native id preserved as provenance.
    """
    session = claude.parse_session(_sess(claude_root, "simple-conversation"))
    assert session.harness == "claude"
    assert session.session_id == "11111111-1111-4111-8111-111111111111"
    assert [m.role for m in session.messages] == ["user", "assistant", "assistant"]
    assert [m.ordinal for m in session.messages] == [0, 1, 2]

    first_assistant = session.messages[1]
    # thinking block dropped -> only the text channel survives
    assert first_assistant.text == "I'll read the file first, then add the function."
    assert len(first_assistant.tool_calls) == 1
    tc = first_assistant.tool_calls[0]
    assert tc.tool_name == "Read"
    assert tc.ordinal == 2  # block index within [thinking(0), text(1), tool_use(2)]
    assert tc.source_tool_use_id == "toolu_001"
    assert tc.tool_input == {"file_path": "/home/user/project/src/utils.py"}


def test_per_message_model_and_token_columns(claude_root: Path) -> None:
    """Each assistant turn carries its model and the four typed token counts."""
    session = claude.parse_session(_sess(claude_root, "simple-conversation"))
    a = session.messages[1]
    assert a.model == "claude-sonnet-4-6"
    assert a.input_tokens == 12
    assert a.output_tokens == 85
    assert a.cache_creation_tokens == 2000
    assert a.cache_read_tokens == 15000
    assert a.source_uuid == "a1111111-0000-4000-8000-000000000002"
    # Claude has no session-grain model rollup (that grain is Cursor's).
    assert session.models is None


def test_tool_result_user_record_dropped_and_parent_resolves_past_it(
    claude_root: Path,
) -> None:
    """An inputs-only ``tool_result`` user record produces no message; the next
    assistant's parent walks past it to the nearest kept ancestor.
    """
    session = claude.parse_session(_sess(claude_root, "simple-conversation"))
    # The dropped tool_result sat between assistant#1 and assistant#2.
    last = session.messages[2]
    assert last.text == "Added `hello()` to `src/utils.py`."
    assert last.parent_ordinal == 1  # resolved past the dropped tool_result turn
    assert last.tool_calls == []


def test_user_content_list_shapes(claude_root: Path) -> None:
    """A user turn whose content is a list of text blocks is kept (joined); a
    user turn whose content is only ``tool_result`` is dropped.
    """
    session = claude.parse_session(
        _sess(claude_root, "pathological-user-content-shapes")
    )
    assert [m.role for m in session.messages] == ["user", "assistant", "assistant"]
    user = session.messages[0]
    assert user.text == "Here is the spec:\nmake it idempotent"
    # The tool_result-only user record was dropped; the trailing assistant
    # resolves its parent past it.
    assert session.messages[2].parent_ordinal == 1


def test_branching_parentuuid_uses_tree_not_position(claude_root: Path) -> None:
    """Multi-model conversation: parents follow the ``parentUuid`` chain (here a
    clean linear chain) and each turn keeps its own model.
    """
    session = claude.parse_session(_sess(claude_root, "pathological-multi-model"))
    models = [m.model for m in session.messages]
    assert models == [None, "claude-sonnet-4-6", None, "claude-opus-4-6"]
    assert [m.parent_ordinal for m in session.messages] == [None, 0, 1, 2]


def test_huge_tool_input_round_trips_untruncated(claude_root: Path) -> None:
    """A large ``tool_input`` is captured whole (no truncation at rest)."""
    path = _sess(claude_root, "pathological-huge-tool-input")
    session = claude.parse_session(path)
    # Recover the original input straight from the fixture to compare against.
    raw = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    expected_input = raw[1]["message"]["content"][1]["input"]
    tc = session.messages[1].tool_calls[0]
    assert tc.tool_name == "Write"
    assert tc.tool_input == expected_input
    assert tc.tool_input["contents"] == expected_input["contents"]


def test_title_agent_name_version_and_time_span(claude_root: Path) -> None:
    """Metadata records fold into the session: ai-title -> title, version is
    captured, and started/ended are the min/max kept-message timestamps.
    """
    session = claude.parse_session(_sess(claude_root, "simple-conversation"))
    assert session.title == "Add hello function to utils"
    assert session.agent_name is None
    assert session.harness_version == "2.1.0"
    assert session.cwd == "/home/user/project"
    assert session.git_branch == "main"
    assert session.started_at is not None
    assert session.ended_at is not None
    assert session.started_at < session.ended_at


def test_custom_title_and_agent_name_with_ignorable_types(claude_root: Path) -> None:
    """The robustness fixture: ignorable record types produce no rows and never
    crash; ``custom-title`` and ``agent-name`` fold into the session.
    """
    session = claude.parse_session(_sess(claude_root, "robustness-record-types"))
    # Only the real user->assistant turn survives the pile of noise records.
    assert [m.role for m in session.messages] == ["user", "assistant"]
    assert [m.ordinal for m in session.messages] == [0, 1]
    assert session.title == "Rename helper + callers"  # custom-title
    assert session.agent_name == "refactorer"


def test_subagent_identity_and_spawn_link(claude_root: Path) -> None:
    """A Claude subagent is its own session: id = file stem (NOT the parent's
    sessionId it carries), parent linkage + spawning_tool_use_id from meta.json,
    agent_name from its agent-name record. The spawn id joins the parent's Task.
    """
    parent_path = _sess(claude_root, "22222222-2222-4222-8222-222222222222")
    sub_dir = parent_path.parent / "22222222-2222-4222-8222-222222222222" / "subagents"
    sub_path = sub_dir / "agent-aaa111.jsonl"
    meta_path = sub_dir / "agent-aaa111.meta.json"

    parent = claude.parse_session(parent_path)
    sub = claude.parse_subagent(sub_path, meta_path=meta_path)

    assert sub.is_subagent is True
    assert sub.session_id == "agent-aaa111"
    assert sub.parent_session_id == "22222222-2222-4222-8222-222222222222"
    assert sub.agent_id == "aaa111"
    assert sub.agent_type == "explore"
    assert sub.spawning_tool_use_id == "toolu_task1"
    assert sub.agent_name == "auth-explore"

    # The spawn id joins the parent's Task tool_use provenance id.
    parent_tool_ids = {
        tc.source_tool_use_id
        for m in parent.messages
        for tc in m.tool_calls
        if tc.tool_name == "Task"
    }
    assert sub.spawning_tool_use_id in parent_tool_ids
