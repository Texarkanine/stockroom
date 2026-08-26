"""Read-time spawn-to-turn association for dashboard session reconstruction.

Slot rule for Cursor is the warehouse-row sibling of ingest's
``_parent_subagent_types``: ``Task`` calls whose ``tool_input.subagent_type``
is not ``None``, in ``(message.ordinal, tool.ordinal)`` order. Candidates are
children with a non-null ``agent_type``, ordered by ``source_path``.

A pill is a positive claim. Missing a placement is acceptable; a guessed turn
is not. Unknown harnesses produce no placements.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any, NamedTuple

_FALLBACK_LABEL = "Subagent"


class ParentTool(NamedTuple):
    """One parent tool call used as a spawn slot or Claude join target."""

    message_ordinal: int
    tool_ordinal: int
    tool_name: str
    tool_input: Mapping[str, Any] | None
    source_tool_use_id: str | None


class ChildSession(NamedTuple):
    """One warehouse child session eligible for association."""

    session_id: str
    agent_type: str | None = None
    agent_name: str | None = None
    title: str | None = None
    spawning_tool_use_id: str | None = None
    source_path: str | None = None


class Placement(NamedTuple):
    """A corroborated child attached to a parent launch ordinal."""

    launch_ordinal: int
    spawn_index: int
    session_id: str
    label: str
    agent_type: str | None
    agent_name: str | None
    title: str | None


def spawn_label(
    *,
    description: str | None = None,
    agent_name: str | None = None,
    title: str | None = None,
    agent_type: str | None = None,
) -> str:
    """Return the first non-empty label in the display fallback chain.

    Order: Task ``description``, ``agent_name``, ``title``, ``agent_type``,
    else ``\"Subagent\"``.
    """
    for value in (description, agent_name, title, agent_type):
        if value:
            return value
    return _FALLBACK_LABEL


def _tool_field(tool: ParentTool, key: str) -> Any:
    payload = tool.tool_input
    if not isinstance(payload, Mapping):
        return None
    return payload.get(key)


def _task_slots(tools: Sequence[ParentTool]) -> list[ParentTool]:
    """Typed Task slots — same rule as ingest ``_parent_subagent_types``."""
    slots = [
        tool
        for tool in tools
        if tool.tool_name == "Task" and _tool_field(tool, "subagent_type") is not None
    ]
    slots.sort(key=lambda tool: (tool.message_ordinal, tool.tool_ordinal))
    return slots


def _to_placement(
    tool: ParentTool,
    child: ChildSession,
    spawn_index: int,
) -> Placement:
    description = _tool_field(tool, "description")
    return Placement(
        launch_ordinal=tool.message_ordinal,
        spawn_index=spawn_index,
        session_id=child.session_id,
        label=spawn_label(
            description=description if isinstance(description, str) else None,
            agent_name=child.agent_name,
            title=child.title,
            agent_type=child.agent_type,
        ),
        agent_type=child.agent_type,
        agent_name=child.agent_name,
        title=child.title,
    )


def _index_placements(
    pairs: Sequence[tuple[ParentTool, ChildSession]],
    *,
    order_key,
) -> list[Placement]:
    grouped: dict[int, list[tuple[ParentTool, ChildSession]]] = {}
    for tool, child in pairs:
        grouped.setdefault(tool.message_ordinal, []).append((tool, child))
    placed: list[Placement] = []
    for ordinal in sorted(grouped):
        group = sorted(grouped[ordinal], key=lambda pair: order_key(pair[1]))
        for spawn_index, (tool, child) in enumerate(group, start=1):
            placed.append(_to_placement(tool, child, spawn_index))
    return placed


def _provenance_join(
    tools: Sequence[ParentTool],
    children: Sequence[ChildSession],
) -> list[Placement]:
    by_id = {tool.source_tool_use_id: tool for tool in tools if tool.source_tool_use_id}
    pairs: list[tuple[ParentTool, ChildSession]] = []
    for child in children:
        tool = by_id.get(child.spawning_tool_use_id or "")
        if tool is None:
            continue
        pairs.append((tool, child))
    return _index_placements(pairs, order_key=lambda child: child.session_id)


def _unique_type_pairs(
    slots: Sequence[ParentTool],
    candidates: Sequence[ChildSession],
) -> list[tuple[ParentTool, ChildSession]]:
    slot_counts = Counter(_tool_field(slot, "subagent_type") for slot in slots)
    child_counts = Counter(child.agent_type for child in candidates)
    slot_by_type = {_tool_field(slot, "subagent_type"): slot for slot in slots}
    pairs: list[tuple[ParentTool, ChildSession]] = []
    for child in candidates:
        agent_type = child.agent_type
        if slot_counts[agent_type] != 1 or child_counts[agent_type] != 1:
            continue
        pairs.append((slot_by_type[agent_type], child))
    return pairs


def _corroborated_zip(
    tools: Sequence[ParentTool],
    children: Sequence[ChildSession],
) -> list[Placement]:
    slots = _task_slots(tools)
    candidates = sorted(
        (child for child in children if child.agent_type is not None),
        key=lambda child: child.source_path or "",
    )
    aligned = len(candidates) == len(slots) and all(
        child.agent_type == _tool_field(slot, "subagent_type")
        for child, slot in zip(candidates, slots, strict=True)
    )
    pairs = (
        list(zip(slots, candidates, strict=True))
        if aligned
        else _unique_type_pairs(slots, candidates)
    )
    return _index_placements(pairs, order_key=lambda child: child.source_path or "")


def associate_children(
    harness: str,
    tools: Sequence[ParentTool],
    children: Sequence[ChildSession],
) -> list[Placement]:
    """Associate child sessions to parent launch turns.

    ``claude`` uses a provenance join on ``spawning_tool_use_id`` =
    ``source_tool_use_id``. ``cursor`` uses a corroborated zip against typed
    Task slots (aligned type sequence, else unique ``agent_type`` pairs).
    Any other harness returns no placements.

    Adding a third harness is the cue to extract ``provenance_join`` /
    ``corroborated_zip`` (order, slots, corroboration) as named techniques,
    not to copy Cursor's Task / ``source_path`` knobs into another ``elif``.
    """
    # Harness → technique map. A third harness should lift the two techniques
    # out rather than copy Cursor's Task / source_path knobs into another elif.
    technique = {
        "claude": _provenance_join,
        "cursor": _corroborated_zip,
    }.get(harness)
    if technique is None:
        return []
    return technique(tools, children)
