"""Per-harness skill-usage extractors for the dashboard metrics layer.

Candidate SQL (in :mod:`stockroom.dashboard.metrics`) filters tool_calls and
user messages in the activity window. This module maps those candidate rows
to normalized :class:`SkillUse` events. Skill naming and invoker rules live
here — not in SQL — so a new harness adds one extractor + registry entry.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterator, Sequence
from pathlib import PurePosixPath
from typing import Any, Literal, NamedTuple

Invoker = Literal["user", "agent"]

_COMMAND_NAME_RE = re.compile(
    r"<command-name>\s*/(?P<name>[^<\s]+)\s*</command-name>",
    re.IGNORECASE,
)
_SKILL_BLOB_PREFIX = "Base directory for this skill:"
_MANUAL_ATTACH_SKILL_NAME_RE = re.compile(
    r"(?m)^Skill Name:\s*(?P<name>\S+)\s*$",
)
#: Claude Code slash commands that are runtime built-ins, not Agent Skills.
#: Bundled skills (e.g. doctor, debug) are intentionally absent — they count.
#: See https://code.claude.com/docs/en/slash-commands
_CLAUDE_BUILTIN_COMMANDS = frozenset(
    {
        "exit",
        "model",
        "plugin",
        "effort",
        "add-dir",
        "reload-plugins",
        "clear",
        "compact",
        "help",
        "login",
        "logout",
        "config",
        "cost",
        "usage",
        "status",
        "bug",
        "memory",
        "vim",
        "permissions",
        "hooks",
        "mcp",
        "rewind",
        "rename",
        "context",
        "todos",
        "init",
        "review",
        "security-review",
        "migrate-installer",
        "terminal-setup",
        "release-notes",
        "upgrade",
        "mobile",
        "voice",
        "insights",
        "export",
        "theme",
        "color",
        "output-style",
        "agents",
        "files",
        "diff",
        "stats",
        "ide",
        "desktop",
        "install-github-app",
        "extra-usage",
        "privacy-settings",
        "keybindings",
        "bashes",
        "plan",
        "fast",
        "think",
    }
)


class SkillUse(NamedTuple):
    """One discrete skill invocation attributed to a harness invoker."""

    skill: str
    invoker: Invoker


#: Row shape from candidate message SQL: ``(harness, text)``.
MessageRow = tuple[str, str | None]
#: Row shape from candidate tool SQL: ``(harness, tool_name, tool_input)``.
ToolRow = tuple[str, str, Any]

ExtractorFn = Callable[
    [Sequence[MessageRow], Sequence[ToolRow]],
    list[SkillUse],
]


def _parse_tool_input(value: Any) -> dict[str, Any]:
    """Normalize DuckDB JSON cells to a dict (empty on failure)."""
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, (bytes, bytearray)):
        value = value.decode("utf-8")
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _skill_from_command_name(text: str) -> str | None:
    match = _COMMAND_NAME_RE.search(text)
    if match is None:
        return None
    name = match.group("name").strip()
    if not name or name in _CLAUDE_BUILTIN_COMMANDS:
        return None
    return name


def _skills_from_manually_attached(text: str) -> list[str]:
    """Return skill names from Cursor ``<manually_attached_skills>`` blocks."""
    if "<manually_attached_skills>" not in text:
        return []
    return [
        match.group("name")
        for match in _MANUAL_ATTACH_SKILL_NAME_RE.finditer(text)
        if match.group("name")
    ]


def _skill_from_read_path(tool_input: dict[str, Any]) -> str | None:
    raw = tool_input.get("path")
    if not isinstance(raw, str) or not raw:
        raw = tool_input.get("file_path")
    if not isinstance(raw, str) or not raw:
        return None
    normalized = raw.replace("\\", "/")
    # Locked rule: path must end with SKILL.md (case-sensitive).
    if not normalized.endswith("SKILL.md"):
        return None
    parent = PurePosixPath(normalized).parent.name
    return parent or None


def extract_claude(
    message_rows: Sequence[MessageRow],
    tool_rows: Sequence[ToolRow],
) -> list[SkillUse]:
    """Extract Claude skill uses from candidate messages and tool calls.

    User: ``<command-name>/NAME</command-name>`` → ``(NAME, "user")`` when
    ``NAME`` is not a Claude Code built-in slash command (``/exit``,
    ``/model``, …). Agent: ``tool_name == "Skill"`` with non-empty
    ``$.skill`` → ``(skill, "agent")``. Synthetic skill-info blobs starting
    with ``Base directory for this skill:`` are ignored.
    """
    events: list[SkillUse] = []
    for _harness, text in message_rows:
        if not text:
            continue
        stripped = text.lstrip()
        if stripped.startswith(_SKILL_BLOB_PREFIX):
            continue
        skill = _skill_from_command_name(text)
        if skill is not None:
            events.append(SkillUse(skill=skill, invoker="user"))

    for _harness, tool_name, tool_input in tool_rows:
        if tool_name != "Skill":
            continue
        payload = _parse_tool_input(tool_input)
        skill = payload.get("skill")
        if isinstance(skill, str) and skill.strip():
            events.append(SkillUse(skill=skill.strip(), invoker="agent"))
    return events


def extract_cursor(
    message_rows: Sequence[MessageRow],
    tool_rows: Sequence[ToolRow],
) -> list[SkillUse]:
    """Extract Cursor skill uses from candidate messages and tool calls.

    User: ``<manually_attached_skills>`` blocks with ``Skill Name: …`` lines
    → ``(name, "user")`` per line. Agent: ``Read`` whose path (``$.path`` or
    ``$.file_path``) ends with ``SKILL.md`` → parent directory basename,
    invoker ``"agent"``.
    """
    events: list[SkillUse] = []
    for _harness, text in message_rows:
        if not text:
            continue
        for skill in _skills_from_manually_attached(text):
            events.append(SkillUse(skill=skill, invoker="user"))

    for _harness, tool_name, tool_input in tool_rows:
        if tool_name != "Read":
            continue
        skill = _skill_from_read_path(_parse_tool_input(tool_input))
        if skill is not None:
            events.append(SkillUse(skill=skill, invoker="agent"))
    return events


EXTRACTORS: dict[str, ExtractorFn] = {
    "claude": extract_claude,
    "cursor": extract_cursor,
}


def iter_skill_uses(
    harness: str,
    message_rows: Sequence[MessageRow],
    tool_rows: Sequence[ToolRow],
) -> Iterator[SkillUse]:
    """Yield skill-use events for ``harness``, or nothing if unregistered."""
    extractor = EXTRACTORS.get(harness)
    if extractor is None:
        return
    yield from extractor(message_rows, tool_rows)
