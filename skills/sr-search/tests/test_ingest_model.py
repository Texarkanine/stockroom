"""Construction/equality tests for the harness-neutral ingest dataclasses.

``stockroom.ingest.model`` is the intermediate representation that decouples
the per-harness parsers (cursor.py / claude.py) from the SQL schema: each
parser's only job is to produce these records, and the writer's only job is to
persist them. The dataclasses mirror the locked ``0001`` schema's
one-meaning-per-field contract, so these tests pin field presence, defaults,
and value-equality (the parser tests and the writer rely on both).
"""

from datetime import datetime

from stockroom.ingest.model import (
    NormalizedMessage,
    NormalizedSession,
    NormalizedToolCall,
)


def test_tool_call_minimal_and_defaults() -> None:
    """A tool call needs only ordinal/name/input; provenance id defaults None."""
    tc = NormalizedToolCall(ordinal=0, tool_name="Read", tool_input={"path": "x"})
    assert tc.ordinal == 0
    assert tc.tool_name == "Read"
    assert tc.tool_input == {"path": "x"}
    assert tc.source_tool_use_id is None


def test_message_minimal_and_defaults() -> None:
    """A message needs only ordinal/role; every other field defaults None/empty."""
    m = NormalizedMessage(ordinal=0, role="user")
    assert m.ordinal == 0
    assert m.role == "user"
    assert m.parent_ordinal is None
    assert m.text is None
    assert m.model is None
    assert m.ts is None
    assert m.input_tokens is None
    assert m.output_tokens is None
    assert m.cache_creation_tokens is None
    assert m.cache_read_tokens is None
    assert m.source_uuid is None
    assert m.tool_calls == []


def test_message_tool_calls_are_independent_per_instance() -> None:
    """The default ``tool_calls`` list is not shared between instances."""
    a = NormalizedMessage(ordinal=0, role="assistant")
    b = NormalizedMessage(ordinal=1, role="assistant")
    a.tool_calls.append(NormalizedToolCall(ordinal=0, tool_name="X", tool_input={}))
    assert a.tool_calls != b.tool_calls
    assert b.tool_calls == []


def test_session_minimal_and_defaults() -> None:
    """A session needs harness/session_id/source_path; the rest default to
    honest absence (None / empty list), never fabricated values.
    """
    s = NormalizedSession(
        harness="cursor",
        session_id="conv-1",
        source_path="/p/conv-1.jsonl",
    )
    assert s.harness == "cursor"
    assert s.session_id == "conv-1"
    assert s.source_path == "/p/conv-1.jsonl"
    assert s.source_mtime is None
    assert s.is_subagent is False
    assert s.project_id is None
    assert s.cwd is None
    assert s.git_branch is None
    assert s.parent_session_id is None
    assert s.agent_id is None
    assert s.agent_type is None
    assert s.spawning_tool_use_id is None
    assert s.agent_name is None
    assert s.models is None
    assert s.title is None
    assert s.harness_version is None
    assert s.started_at is None
    assert s.ended_at is None
    assert s.messages == []


def test_value_equality_across_instances() -> None:
    """Dataclasses compare by value, so equal content compares equal."""
    ts = datetime(2026, 1, 1, 0, 0, 0)
    mk = lambda: NormalizedSession(  # noqa: E731 - terse builder for the assert
        harness="claude",
        session_id="s1",
        source_path="/p/s1.jsonl",
        messages=[
            NormalizedMessage(
                ordinal=0,
                role="assistant",
                text="hi",
                ts=ts,
                tool_calls=[
                    NormalizedToolCall(
                        ordinal=0,
                        tool_name="Read",
                        tool_input={"file_path": "/a"},
                        source_tool_use_id="toolu_1",
                    )
                ],
            )
        ],
    )
    assert mk() == mk()


def test_session_messages_are_independent_per_instance() -> None:
    """The default ``messages`` list is not shared between session instances."""
    a = NormalizedSession(harness="cursor", session_id="a", source_path="/a")
    b = NormalizedSession(harness="cursor", session_id="b", source_path="/b")
    a.messages.append(NormalizedMessage(ordinal=0, role="user"))
    assert b.messages == []
