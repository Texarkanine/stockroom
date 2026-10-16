"""Unit contracts for dashboard spawn-to-turn association."""

import pytest

from stockroom.dashboard.spawns import (
    ChildSession,
    ParentTool,
    Placement,
    associate_children,
    spawn_label,
)


def _tool(
    *,
    message_ordinal: int,
    tool_ordinal: int = 0,
    tool_name: str = "Task",
    description: str | None = None,
    subagent_type: str | None = None,
    source_tool_use_id: str | None = None,
) -> ParentTool:
    payload: dict[str, str] = {}
    if description is not None:
        payload["description"] = description
    if subagent_type is not None:
        payload["subagent_type"] = subagent_type
    return ParentTool(
        message_ordinal=message_ordinal,
        tool_ordinal=tool_ordinal,
        tool_name=tool_name,
        tool_input=payload,
        source_tool_use_id=source_tool_use_id,
    )


def _child(
    session_id: str,
    *,
    agent_type: str | None = None,
    agent_name: str | None = None,
    title: str | None = None,
    spawning_tool_use_id: str | None = None,
    source_path: str | None = None,
) -> ChildSession:
    return ChildSession(
        session_id=session_id,
        agent_type=agent_type,
        agent_name=agent_name,
        title=title,
        spawning_tool_use_id=spawning_tool_use_id,
        source_path=source_path,
    )


def _placement(
    *,
    launch_ordinal: int,
    spawn_index: int,
    session_id: str,
    label: str,
    agent_type: str | None = None,
    agent_name: str | None = None,
    title: str | None = None,
) -> Placement:
    return Placement(
        launch_ordinal=launch_ordinal,
        spawn_index=spawn_index,
        session_id=session_id,
        label=label,
        agent_type=agent_type,
        agent_name=agent_name,
        title=title,
    )


def test_claude_join_places_child_on_matching_tool_ordinal() -> None:
    tools = [
        _tool(
            message_ordinal=0,
            description="Look around",
            source_tool_use_id="toolu_join",
        )
    ]
    children = [
        _child(
            "kid-a",
            agent_type="explore",
            spawning_tool_use_id="toolu_join",
        )
    ]
    assert associate_children("claude", tools, children) == [
        _placement(
            launch_ordinal=0,
            spawn_index=1,
            session_id="kid-a",
            label="Look around",
            agent_type="explore",
        )
    ]


def test_claude_unmatched_or_missing_spawn_id_is_omitted() -> None:
    tools = [
        _tool(message_ordinal=3, source_tool_use_id="toolu_real"),
        _tool(message_ordinal=4, tool_name="Read"),
    ]
    children = [
        _child("missing-id", spawning_tool_use_id=None, agent_type="explore"),
        _child("no-join", spawning_tool_use_id="toolu_other", agent_type="explore"),
    ]
    assert associate_children("claude", tools, children) == []


def test_cursor_aligned_zip_places_all_when_counts_and_types_match() -> None:
    tools = [
        _tool(
            message_ordinal=2,
            description="Search",
            subagent_type="explore",
        ),
        _tool(
            message_ordinal=8,
            tool_ordinal=1,
            description="Build it",
            subagent_type="generalPurpose",
        ),
    ]
    children = [
        _child(
            "later",
            agent_type="generalPurpose",
            source_path="/tmp/b.jsonl",
        ),
        _child(
            "first",
            agent_type="explore",
            source_path="/tmp/a.jsonl",
        ),
    ]
    assert associate_children("cursor", tools, children) == [
        _placement(
            launch_ordinal=2,
            spawn_index=1,
            session_id="first",
            label="Search",
            agent_type="explore",
        ),
        _placement(
            launch_ordinal=8,
            spawn_index=1,
            session_id="later",
            label="Build it",
            agent_type="generalPurpose",
        ),
    ]


def test_cursor_untyped_task_does_not_consume_a_slot() -> None:
    tools = [
        _tool(
            message_ordinal=48,
            description="Do the work",
            subagent_type="generalPurpose",
        ),
        _tool(message_ordinal=55, description="Nudge L3 QA"),
    ]
    children = [
        _child(
            "bc96",
            agent_type="generalPurpose",
            source_path="/tmp/bc96.jsonl",
        )
    ]
    assert associate_children("cursor", tools, children) == [
        _placement(
            launch_ordinal=48,
            spawn_index=1,
            session_id="bc96",
            label="Do the work",
            agent_type="generalPurpose",
        )
    ]


def test_cursor_unique_type_places_remaining_pair_when_sibling_missing() -> None:
    tools = [
        _tool(message_ordinal=10, subagent_type="explore", description="Dig"),
        _tool(message_ordinal=20, subagent_type="generalPurpose"),
    ]
    children = [
        _child("only-explore", agent_type="explore", source_path="/tmp/e.jsonl")
    ]
    assert associate_children("cursor", tools, children) == [
        _placement(
            launch_ordinal=10,
            spawn_index=1,
            session_id="only-explore",
            label="Dig",
            agent_type="explore",
        )
    ]


def test_cursor_count_mismatch_with_colliding_types_places_nothing() -> None:
    tools = [
        _tool(message_ordinal=1, subagent_type="explore"),
        _tool(message_ordinal=2, subagent_type="generalPurpose"),
        _tool(message_ordinal=3, subagent_type="explore"),
    ]
    children = [
        _child("e1", agent_type="explore", source_path="/tmp/1.jsonl"),
        _child("e2", agent_type="explore", source_path="/tmp/2.jsonl"),
    ]
    assert associate_children("cursor", tools, children) == []


def test_cursor_extra_child_is_omitted_not_leftover() -> None:
    tools = [
        _tool(message_ordinal=4, subagent_type="generalPurpose", description="Main")
    ]
    children = [
        _child("kept", agent_type="generalPurpose", source_path="/tmp/a.jsonl"),
        _child("extra", agent_type="explore", source_path="/tmp/b.jsonl"),
    ]
    assert associate_children("cursor", tools, children) == [
        _placement(
            launch_ordinal=4,
            spawn_index=1,
            session_id="kept",
            label="Main",
            agent_type="generalPurpose",
        )
    ]
    same_type_extra = [
        _child("one", agent_type="generalPurpose", source_path="/tmp/a.jsonl"),
        _child("two", agent_type="generalPurpose", source_path="/tmp/b.jsonl"),
    ]
    assert associate_children("cursor", tools, same_type_extra) == []


def test_cursor_null_agent_type_is_omitted() -> None:
    tools = [_tool(message_ordinal=9, subagent_type="generalPurpose")]
    children = [
        _child("unknown", agent_type=None, source_path="/tmp/z.jsonl"),
    ]
    assert associate_children("cursor", tools, children) == []


def test_cursor_type_sequence_mismatch_does_not_zip() -> None:
    tools = [
        _tool(message_ordinal=1, subagent_type="explore", description="A"),
        _tool(message_ordinal=2, subagent_type="generalPurpose", description="B"),
    ]
    swapped = [
        _child("gp", agent_type="generalPurpose", source_path="/tmp/a.jsonl"),
        _child("ex", agent_type="explore", source_path="/tmp/b.jsonl"),
    ]
    assert associate_children("cursor", tools, swapped) == [
        _placement(
            launch_ordinal=1,
            spawn_index=1,
            session_id="ex",
            label="A",
            agent_type="explore",
        ),
        _placement(
            launch_ordinal=2,
            spawn_index=1,
            session_id="gp",
            label="B",
            agent_type="generalPurpose",
        ),
    ]
    colliding = [
        _child("e1", agent_type="explore", source_path="/tmp/a.jsonl"),
        _child("e2", agent_type="explore", source_path="/tmp/b.jsonl"),
    ]
    assert associate_children("cursor", tools, colliding) == []


def test_two_children_on_one_turn_get_spawn_index_1_then_2() -> None:
    tools = [
        _tool(
            message_ordinal=48,
            tool_ordinal=0,
            description="First",
            subagent_type="explore",
            source_tool_use_id="toolu_a",
        ),
        _tool(
            message_ordinal=48,
            tool_ordinal=1,
            description="Second",
            subagent_type="generalPurpose",
            source_tool_use_id="toolu_b",
        ),
    ]
    claude_children = [
        _child("zeta", spawning_tool_use_id="toolu_b", agent_type="generalPurpose"),
        _child("alpha", spawning_tool_use_id="toolu_a", agent_type="explore"),
    ]
    assert associate_children("claude", tools, claude_children) == [
        _placement(
            launch_ordinal=48,
            spawn_index=1,
            session_id="alpha",
            label="First",
            agent_type="explore",
        ),
        _placement(
            launch_ordinal=48,
            spawn_index=2,
            session_id="zeta",
            label="Second",
            agent_type="generalPurpose",
        ),
    ]
    cursor_children = [
        _child("later", agent_type="generalPurpose", source_path="/tmp/b.jsonl"),
        _child("earlier", agent_type="explore", source_path="/tmp/a.jsonl"),
    ]
    assert associate_children("cursor", tools, cursor_children) == [
        _placement(
            launch_ordinal=48,
            spawn_index=1,
            session_id="earlier",
            label="First",
            agent_type="explore",
        ),
        _placement(
            launch_ordinal=48,
            spawn_index=2,
            session_id="later",
            label="Second",
            agent_type="generalPurpose",
        ),
    ]


def test_spawn_label_falls_through_description_name_title_type() -> None:
    assert (
        spawn_label(
            description="Task prompt",
            agent_name="Ada",
            title="T",
            agent_type="explore",
        )
        == "Task prompt"
    )
    assert spawn_label(description="", agent_name="Ada", title="T") == "Ada"
    assert spawn_label(agent_name="", title="Child title") == "Child title"
    assert spawn_label(title="", agent_type="explore") == "explore"
    assert spawn_label() == "Subagent"


def test_unknown_harness_places_nothing() -> None:
    tools = [_tool(message_ordinal=1, subagent_type="explore", source_tool_use_id="t")]
    children = [
        _child("kid", agent_type="explore", spawning_tool_use_id="t", source_path="a")
    ]
    assert associate_children("gemini", tools, children) == []
    assert associate_children("codex", tools, children) == []


def _wrapped_task(
    *,
    message_ordinal: int,
    description: str,
    subagent_type: str | None,
    source_tool_use_id: str | None = None,
    tool_ordinal: int = 0,
    namespace: str = "cursor",
    inner_tool_name: str = "Task",
) -> ParentTool:
    arguments: dict[str, str] = {}
    if description:
        arguments["description"] = description
    if subagent_type is not None:
        arguments["subagent_type"] = subagent_type
    return ParentTool(
        message_ordinal=message_ordinal,
        tool_ordinal=tool_ordinal,
        tool_name="CallDynamicTool",
        tool_input={
            "namespace": namespace,
            "toolName": inner_tool_name,
            "arguments": arguments,
        },
        source_tool_use_id=source_tool_use_id,
    )


def test_cursor_wrapped_task_places_like_a_native_task() -> None:
    """A cursor/Task CallDynamicTool is a slot, and the label is the nested description."""
    tools = [
        _wrapped_task(
            message_ordinal=42,
            description="Niko QA for git-wt",
            subagent_type="generalPurpose",
            source_tool_use_id="call-1\nfc_2",
        )
    ]
    children = [
        _child(
            "43b093cd",
            agent_type="generalPurpose",
            source_path="/tmp/z-store.db",
        )
    ]
    assert associate_children("cursor", tools, children) == [
        _placement(
            launch_ordinal=42,
            spawn_index=1,
            session_id="43b093cd",
            label="Niko QA for git-wt",
            agent_type="generalPurpose",
        )
    ]


def test_cursor_spawn_id_places_the_matching_child_only() -> None:
    """An id match wins, and the earlier same-type child is not zipped in."""
    tool_call_id = "call-1\nfc_2"
    tools = [
        _wrapped_task(
            message_ordinal=42,
            description="Niko QA for git-wt",
            subagent_type="generalPurpose",
            source_tool_use_id=tool_call_id,
        )
    ]
    children = [
        _child(
            "earlier-path",
            agent_type="generalPurpose",
            source_path="/tmp/a-store.db",
            spawning_tool_use_id="unrelated",
        ),
        _child(
            "matching-id",
            agent_type="generalPurpose",
            source_path="/tmp/z-store.db",
            spawning_tool_use_id=tool_call_id,
        ),
    ]
    assert associate_children("cursor", tools, children) == [
        _placement(
            launch_ordinal=42,
            spawn_index=1,
            session_id="matching-id",
            label="Niko QA for git-wt",
            agent_type="generalPurpose",
        )
    ]


@pytest.mark.parametrize(
    ("namespace", "inner_tool_name", "subagent_type"),
    [
        ("cursor", "browser_cdp", "generalPurpose"),
        ("other", "Task", "generalPurpose"),
        ("cursor", "Task", None),
    ],
)
def test_cursor_call_dynamic_tool_that_is_not_a_typed_task_is_not_a_slot(
    namespace: str, inner_tool_name: str, subagent_type: str | None
) -> None:
    """A non-Task name, a non-cursor namespace, or a null nested type adds no slot."""
    tools = [
        _wrapped_task(
            message_ordinal=3,
            description="Not a spawn",
            subagent_type=subagent_type,
            namespace=namespace,
            inner_tool_name=inner_tool_name,
        )
    ]
    children = [_child("kid", agent_type="generalPurpose", source_path="/tmp/kid")]
    assert associate_children("cursor", tools, children) == []


def test_cursor_child_with_unmatched_spawn_id_is_omitted() -> None:
    """A spawn id that matches no slot stays out, even when the type is unique."""
    tools = [
        _tool(
            message_ordinal=7,
            description="Search",
            subagent_type="explore",
            source_tool_use_id="tool-real",
        )
    ]
    children = [
        _child(
            "wrong-id",
            agent_type="explore",
            source_path="/tmp/wrong.jsonl",
            spawning_tool_use_id="tool-other",
        )
    ]
    assert associate_children("cursor", tools, children) == []
