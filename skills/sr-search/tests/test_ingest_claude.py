"""Claude Code parser tests.

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
from datetime import datetime
from pathlib import Path

import duckdb

from stockroom.ingest import claude, writer


def _write_user_session(path: Path, *, timestamp: object) -> Path:
    """Write a minimal one-user-turn Claude transcript with the given timestamp."""
    record = {
        "type": "user",
        "message": {"role": "user", "content": "hello"},
        "uuid": "a1111111-0000-4000-8000-000000000001",
        "parentUuid": None,
        "timestamp": timestamp,
        "sessionId": "ts-session",
        "cwd": "/tmp/proj",
    }
    path.write_text(json.dumps(record) + "\n", encoding="utf-8")
    return path


def test_parse_session_z_suffix_timestamp_is_naive_utc(tmp_path: Path) -> None:
    """Trailing ``Z`` message stamps become naive UTC on the public session."""
    path = _write_user_session(
        tmp_path / "z.jsonl", timestamp="2026-07-10T03:22:00.000Z"
    )
    session = claude.parse_session(path)
    assert session.messages[0].ts == datetime(2026, 7, 10, 3, 22, 0)
    assert session.messages[0].ts.tzinfo is None
    assert session.started_at == datetime(2026, 7, 10, 3, 22, 0)


def test_parse_session_offset_timestamp_converts_to_naive_utc(tmp_path: Path) -> None:
    """Offset-aware message stamps convert to UTC before tzinfo is dropped."""
    path = _write_user_session(
        tmp_path / "offset.jsonl", timestamp="2026-07-09T22:22:00-05:00"
    )
    session = claude.parse_session(path)
    assert session.messages[0].ts == datetime(2026, 7, 10, 3, 22, 0)
    assert session.messages[0].ts.tzinfo is None


def test_parse_session_rejects_non_string_timestamps(tmp_path: Path) -> None:
    """Non-string / empty timestamps yield ``None`` on the public message."""
    for i, bad in enumerate((None, "", 123)):
        path = _write_user_session(tmp_path / f"bad-{i}.jsonl", timestamp=bad)
        session = claude.parse_session(path)
        assert session.messages[0].ts is None
        assert session.started_at is None


def _write_session_with_entrypoint(path: Path, *, entrypoint: str | None) -> Path:
    """Write a minimal Claude transcript optionally carrying ``entrypoint``."""
    record = {
        "type": "user",
        "message": {"role": "user", "content": "hello"},
        "uuid": "a1111111-0000-4000-8000-000000000001",
        "parentUuid": None,
        "timestamp": "2026-07-10T03:22:00.000Z",
        "sessionId": "ep-session",
        "cwd": "/tmp/proj",
    }
    if entrypoint is not None:
        record["entrypoint"] = entrypoint
    path.write_text(json.dumps(record) + "\n", encoding="utf-8")
    return path


def test_parse_session_passthrough_entrypoint_cli(tmp_path: Path) -> None:
    """Native ``entrypoint: cli`` on a record becomes ``session.entrypoint``."""
    path = _write_session_with_entrypoint(tmp_path / "cli.jsonl", entrypoint="cli")
    session = claude.parse_session(path)
    assert session.entrypoint == "cli"


def test_parse_session_passthrough_entrypoint_claude_desktop(tmp_path: Path) -> None:
    """Native ``entrypoint: claude-desktop`` is stored as the raw string."""
    path = _write_session_with_entrypoint(
        tmp_path / "desktop.jsonl", entrypoint="claude-desktop"
    )
    session = claude.parse_session(path)
    assert session.entrypoint == "claude-desktop"


def test_parse_session_missing_entrypoint_is_none(tmp_path: Path) -> None:
    """Absent ``entrypoint`` leaves ``session.entrypoint`` as ``None``."""
    path = _write_session_with_entrypoint(tmp_path / "none.jsonl", entrypoint=None)
    session = claude.parse_session(path)
    assert session.entrypoint is None


def test_parse_session_unknown_entrypoint_stored_raw(tmp_path: Path) -> None:
    """Unknown entrypoint strings are stored verbatim (no allowlist)."""
    path = _write_session_with_entrypoint(
        tmp_path / "weird.jsonl", entrypoint="future-surface"
    )
    session = claude.parse_session(path)
    assert session.entrypoint == "future-surface"


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


def _dump(path: Path, records: list[dict]) -> Path:
    """Write ``records`` as JSONL."""
    path.write_text(
        "".join(json.dumps(record) + "\n" for record in records),
        encoding="utf-8",
    )
    return path


def _usage(
    input_tokens: int,
    cache_creation: int,
    cache_read: int,
    output: int,
) -> dict:
    """One Claude ``message.usage`` object."""
    return {
        "input_tokens": input_tokens,
        "cache_creation_input_tokens": cache_creation,
        "cache_read_input_tokens": cache_read,
        "output_tokens": output,
    }


def _assistant_line(
    *,
    uuid: str,
    parent: str | None,
    content: list,
    usage: dict | None,
    message_id: str | None = "msg_FAKE1",
    request_id: str | None = "req_FAKE1",
) -> dict:
    """One Claude assistant transcript line."""
    message: dict = {
        "role": "assistant",
        "model": "claude-opus-5-5",
        "content": content,
    }
    if message_id is not None:
        message["id"] = message_id
    if usage is not None:
        message["usage"] = usage
    record: dict = {
        "type": "assistant",
        "uuid": uuid,
        "parentUuid": parent,
        "sessionId": "00000000-0000-4000-8000-000000000001",
        "timestamp": "2026-10-01T12:00:01.000Z",
        "message": message,
    }
    if request_id is not None:
        record["requestId"] = request_id
    return record


def _user_line() -> dict:
    """The report's user line."""
    return {
        "type": "user",
        "uuid": "u-1",
        "parentUuid": None,
        "sessionId": "00000000-0000-4000-8000-000000000001",
        "timestamp": "2026-10-01T12:00:00.000Z",
        "message": {"role": "user", "content": "hello"},
    }


def _multi_block_records() -> list[dict]:
    """The report's thinking / text / tool_use split of one API response.

    A trailing assistant line carries an empty ``usage`` object and its own
    API identity, so it must not pick up the response's counts.
    """
    shared = _usage(2, 1000, 50000, 8)
    return [
        _user_line(),
        _assistant_line(
            uuid="a-1",
            parent="u-1",
            content=[{"type": "thinking", "thinking": "", "signature": "x"}],
            usage=shared,
        ),
        _assistant_line(
            uuid="a-2",
            parent="a-1",
            content=[{"type": "text", "text": "ok"}],
            usage=shared,
        ),
        _assistant_line(
            uuid="a-3",
            parent="a-2",
            content=[
                {
                    "type": "tool_use",
                    "id": "toolu_FAKE1",
                    "name": "Bash",
                    "input": {"command": "true"},
                }
            ],
            usage=_usage(2, 1000, 50000, 120),
        ),
        _assistant_line(
            uuid="a-4",
            parent="a-3",
            content=[{"type": "text", "text": "no usage"}],
            usage={},
            message_id="msg_EMPTY",
            request_id="req_EMPTY",
        ),
    ]


def _token_tuple(message: claude.NormalizedMessage) -> tuple:
    """The four token columns on one message."""
    return (
        message.input_tokens,
        message.cache_creation_tokens,
        message.cache_read_tokens,
        message.output_tokens,
    )


def _assistant_sums(session: claude.NormalizedSession) -> tuple[int, int, int, int]:
    """Sum non-NULL assistant token columns in report order."""
    assistants = [m for m in session.messages if m.role == "assistant"]

    def _sum(name: str) -> int:
        return sum(
            value
            for message in assistants
            if (value := getattr(message, name)) is not None
        )

    return (
        _sum("input_tokens"),
        _sum("cache_creation_tokens"),
        _sum("cache_read_tokens"),
        _sum("output_tokens"),
    )


def test_multi_block_response_attributes_usage_once(tmp_path: Path) -> None:
    """A multi-block Claude response keeps one row per line and one copy of usage.

    Thinking, text, and tool_use lines that share ``message.id`` and
    ``requestId`` stay separate messages. Text and the tool call survive.
    Exactly one row keeps tokens. The four sums are the field-wise max
    ``(2, 1000, 50000, 120)``. User rows stay NULL. An assistant line with
    empty usage stays NULL and does not raise.
    """
    session = claude.parse_session(
        _dump(tmp_path / "multi.jsonl", _multi_block_records())
    )
    assert [m.role for m in session.messages] == [
        "user",
        "assistant",
        "assistant",
        "assistant",
        "assistant",
    ]
    user, thinking, text, tool, empty = session.messages
    assert _token_tuple(user) == (None, None, None, None)
    assert thinking.text is None
    assert text.text == "ok"
    assert tool.tool_calls[0].tool_name == "Bash"
    assert tool.tool_calls[0].source_tool_use_id == "toolu_FAKE1"
    assert _token_tuple(thinking) == (None, None, None, None)
    assert _token_tuple(text) == (None, None, None, None)
    assert _token_tuple(tool) == (2, 1000, 50000, 120)
    assert _token_tuple(empty) == (None, None, None, None)
    assert _assistant_sums(session) == (2, 1000, 50000, 120)


def test_fieldwise_max_when_last_line_output_is_lower(tmp_path: Path) -> None:
    """Output attribution is the field-wise max, not the last line's usage.

    When an earlier line in the same response has a higher ``output_tokens``
    than the last line, the summed output is that max.
    """
    records = [
        _assistant_line(
            uuid="a-1",
            parent=None,
            content=[{"type": "text", "text": "earlier"}],
            usage=_usage(1, 0, 0, 50),
        ),
        _assistant_line(
            uuid="a-2",
            parent="a-1",
            content=[{"type": "text", "text": "later"}],
            usage=_usage(9, 0, 0, 10),
        ),
    ]
    session = claude.parse_session(_dump(tmp_path / "max.jsonl", records))
    assert _assistant_sums(session) == (9, 0, 0, 50)
    assert _token_tuple(session.messages[0]) == (None, None, None, None)
    assert _token_tuple(session.messages[1]) == (9, 0, 0, 50)


def test_distinct_api_responses_are_both_counted(tmp_path: Path) -> None:
    """Two assistant responses with different API identities are both summed."""
    records = [
        _assistant_line(
            uuid="a-1",
            parent=None,
            content=[{"type": "text", "text": "one"}],
            usage=_usage(2, 0, 0, 10),
            message_id="msg_A",
            request_id="req_A",
        ),
        _assistant_line(
            uuid="a-2",
            parent="a-1",
            content=[{"type": "text", "text": "two"}],
            usage=_usage(3, 1, 4, 20),
            message_id="msg_B",
            request_id="req_B",
        ),
    ]
    session = claude.parse_session(_dump(tmp_path / "two.jsonl", records))
    assert _assistant_sums(session) == (5, 1, 4, 30)


def test_lines_without_api_identity_keep_their_own_usage(tmp_path: Path) -> None:
    """Assistant lines missing ``message.id`` or ``requestId`` are not merged.

    Identical usage on unkeyed lines is kept on each line.
    """
    records = [
        _assistant_line(
            uuid="a-1",
            parent=None,
            content=[{"type": "text", "text": "no request"}],
            usage=_usage(4, 0, 0, 7),
            message_id="msg_ONLY",
            request_id=None,
        ),
        _assistant_line(
            uuid="a-2",
            parent="a-1",
            content=[{"type": "text", "text": "no message id"}],
            usage=_usage(4, 0, 0, 7),
            message_id=None,
            request_id="req_ONLY",
        ),
    ]
    session = claude.parse_session(_dump(tmp_path / "unkeyed.jsonl", records))
    assert _token_tuple(session.messages[0]) == (4, 0, 0, 7)
    assert _token_tuple(session.messages[1]) == (4, 0, 0, 7)
    assert _assistant_sums(session) == (8, 0, 0, 14)


def test_response_usage_attribution_is_idempotent(tmp_path: Path) -> None:
    """Parsing the same multi-block file twice yields the same token columns."""
    path = _dump(tmp_path / "multi.jsonl", _multi_block_records())
    first = [_token_tuple(m) for m in claude.parse_session(path).messages]
    second = [_token_tuple(m) for m in claude.parse_session(path).messages]
    assert first == second


def test_multi_block_response_rolls_up_once_in_session_token_usage(
    tmp_path: Path,
    migrated_con: duckdb.DuckDBPyConnection,
) -> None:
    """Writing a multi-block response rolls up once in ``session_token_usage``.

    Totals equal ``(2, 1000, 50000, 120)`` and ``token_grain`` is ``message``.
    """
    session = claude.parse_session(
        _dump(tmp_path / "multi.jsonl", _multi_block_records())
    )
    writer.write_session(migrated_con, session)
    row = migrated_con.execute(
        "SELECT input_tokens_total, cache_creation_tokens_total, "
        "cache_read_tokens_total, output_tokens_total, token_grain "
        "FROM session_token_usage WHERE session_id = ?",
        [session.session_id],
    ).fetchone()
    assert row == (2, 1000, 50000, 120, "message")
