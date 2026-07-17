"""Skill-usage extractors and metrics.skills contracts for the dashboard."""

from __future__ import annotations

import json
from datetime import datetime

import duckdb

from stockroom.dashboard import metrics, skill_usage


# ---------------------------------------------------------------------------
# Real-shaped warehouse fixture strings (Claude command-name, Skill tool,
# Cursor SKILL.md Read path). Used by extractor unit tests.
# ---------------------------------------------------------------------------

CLAUDE_COMMAND_NAME_TEXT = (
    "<command-message>niko is running…</command-message>\n"
    "<command-name>/niko</command-name>\n"
    "<command-args>plan skill usage</command-args>"
)

CLAUDE_BUILTIN_EXIT_TEXT = (
    "<command-name>/exit</command-name>\n"
    "            <command-message>exit</command-message>\n"
    "            <command-args></command-args>"
)

CLAUDE_PLUGIN_SKILL_TEXT = (
    "<command-message>stockroom:sr-search</command-message>\n"
    "<command-name>/stockroom:sr-search</command-name>"
)

CLAUDE_SKILL_BLOB_TEXT = (
    "Base directory for this skill: /home/user/.claude/skills/niko\n"
    "\n"
    "You need to solve this question using niko skill."
)

CLAUDE_SKILL_TOOL_INPUT = '{"skill": "niko", "args": "plan"}'

CURSOR_SKILL_MD_READ_INPUT = (
    '{"path": "/home/user/.cursor/skills/shared/niko/SKILL.md"}'
)

CURSOR_MANUALLY_ATTACHED_TEXT = (
    "<manually_attached_skills>\n"
    "The user has manually attached the following skills to their message.\n"
    "These skills contain specific instructions or workflows that the user "
    "wants you to follow for this request.\n"
    "Only read the files if needed, the full skill content is inlined here.\n"
    "\n"
    "Skill Name: niko-build\n"
    "Path: \\home\\user\\.cursor\\skills\\shared\\niko-build\\SKILL.md\n"
    "SKILL.md content:\n"
    "# Build Phase\n"
    "</manually_attached_skills>\n"
    "<user_query>\ndo the thing\n</user_query>"
)

CURSOR_MANUALLY_ATTACHED_MULTI_TEXT = (
    "<manually_attached_skills>\n"
    "Skill Name: niko-archive\n"
    "Path: /skills/niko-archive/SKILL.md\n"
    "Skill Name: sr-query\n"
    "Path: /skills/sr-query/SKILL.md\n"
    "</manually_attached_skills>"
)


def _seed_session(
    con: duckdb.DuckDBPyConnection,
    *,
    harness: str,
    session_id: str,
    activity: datetime,
    project_id: str = "proj",
    message_count: int = 1,
    started_at: datetime | None = None,
) -> None:
    """Insert one main session and a deterministic run of messages."""
    con.execute(
        "INSERT INTO sessions "
        "(harness, session_id, project_id, cwd, workspace_key, source_path, "
        "is_subagent, started_at, source_mtime) "
        "VALUES (?, ?, ?, NULL, NULL, ?, false, ?, ?)",
        [
            harness,
            session_id,
            project_id,
            f"/tmp/{session_id}.jsonl",
            started_at,
            activity,
        ],
    )
    for ordinal in range(message_count):
        con.execute(
            "INSERT INTO messages "
            "(harness, session_id, message_id, ordinal, role, text, first_seen_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                harness,
                session_id,
                f"{session_id}#{ordinal}",
                ordinal,
                "user" if ordinal == 0 else "assistant",
                f"message {ordinal}",
                activity,
            ],
        )


def _seed_tool(
    con: duckdb.DuckDBPyConnection,
    *,
    harness: str,
    session_id: str,
    ordinal: int,
    tool_name: str,
    message_ordinal: int = 0,
    tool_input: object | None = None,
) -> None:
    payload = "{}" if tool_input is None else json.dumps(tool_input)
    con.execute(
        "INSERT INTO tool_calls "
        "(harness, session_id, message_id, ordinal, tool_name, tool_input) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        [
            harness,
            session_id,
            f"{session_id}#{message_ordinal}",
            ordinal,
            tool_name,
            payload,
        ],
    )


# --- Extractor unit tests -------------------------------------------------


def _as_events(uses: list[skill_usage.SkillUse]) -> list[tuple[str, str]]:
    return [(use.skill, use.invoker) for use in uses]


class TestExtractClaude:
    """Claude harness: user command-name and agent Skill tool events."""

    def test_user_command_name_yields_user_event(self) -> None:
        """Claude user message with <command-name>/… maps to (skill, user)."""
        messages: list[skill_usage.MessageRow] = [
            ("claude", CLAUDE_COMMAND_NAME_TEXT),
        ]
        assert _as_events(skill_usage.extract_claude(messages, [])) == [
            ("niko", "user"),
        ]

    def test_skill_tool_yields_agent_event(self) -> None:
        """Claude Skill tool with $.skill maps to (skill, agent)."""
        tools: list[skill_usage.ToolRow] = [
            ("claude", "Skill", json.loads(CLAUDE_SKILL_TOOL_INPUT)),
        ]
        assert _as_events(skill_usage.extract_claude([], tools)) == [
            ("niko", "agent"),
        ]

    def test_skill_blob_user_message_yields_nothing(self) -> None:
        """Synthetic 'Base directory for this skill:' blobs are ignored."""
        messages: list[skill_usage.MessageRow] = [
            ("claude", CLAUDE_SKILL_BLOB_TEXT),
        ]
        assert skill_usage.extract_claude(messages, []) == []

    def test_non_skill_user_and_tool_yield_nothing(self) -> None:
        """Ordinary Claude user text and non-Skill tools emit no events."""
        messages: list[skill_usage.MessageRow] = [
            ("claude", "please fix the flaky test"),
        ]
        tools: list[skill_usage.ToolRow] = [
            ("claude", "Read", {"file_path": "/home/user/project/src/utils.py"}),
            ("claude", "Bash", {"command": "make test"}),
        ]
        assert skill_usage.extract_claude(messages, tools) == []

    def test_empty_skill_string_on_tool_is_dropped(self) -> None:
        """Skill tool with empty $.skill does not emit an event."""
        tools: list[skill_usage.ToolRow] = [
            ("claude", "Skill", {"skill": ""}),
            ("claude", "Skill", {"skill": None}),
            ("claude", "Skill", {}),
        ]
        assert skill_usage.extract_claude([], tools) == []

    def test_multiple_events_in_one_session_all_count(self) -> None:
        """Command-name + Skill tool in one session each produce an event."""
        messages: list[skill_usage.MessageRow] = [
            ("claude", CLAUDE_COMMAND_NAME_TEXT),
        ]
        tools: list[skill_usage.ToolRow] = [
            ("claude", "Skill", {"skill": "gm"}),
            ("claude", "Skill", json.loads(CLAUDE_SKILL_TOOL_INPUT)),
        ]
        assert _as_events(skill_usage.extract_claude(messages, tools)) == [
            ("niko", "user"),
            ("gm", "agent"),
            ("niko", "agent"),
        ]

    def test_builtin_slash_commands_are_not_skills(self) -> None:
        """Claude built-ins like /exit and /model are not skill uses."""
        messages: list[skill_usage.MessageRow] = [
            ("claude", CLAUDE_BUILTIN_EXIT_TEXT),
            (
                "claude",
                "<command-name>/model</command-name>\n"
                "<command-message>model</command-message>\n"
                "<command-args></command-args>",
            ),
            (
                "claude",
                "<command-name>/plugin</command-name>\n"
                "<command-message>plugin</command-message>",
            ),
        ]
        assert skill_usage.extract_claude(messages, []) == []

    def test_plugin_namespaced_command_name_is_a_skill(self) -> None:
        """Plugin skills like /stockroom:sr-search still count as user skills."""
        messages: list[skill_usage.MessageRow] = [
            ("claude", CLAUDE_PLUGIN_SKILL_TEXT),
        ]
        assert _as_events(skill_usage.extract_claude(messages, [])) == [
            ("stockroom:sr-search", "user"),
        ]


class TestExtractCursor:
    """Cursor harness: agent Read of …/SKILL.md; user manually_attached_skills."""

    def test_read_skill_md_path_yields_agent_event(self) -> None:
        """Cursor Read ending in /SKILL.md → (parent basename, agent)."""
        tools: list[skill_usage.ToolRow] = [
            ("cursor", "Read", json.loads(CURSOR_SKILL_MD_READ_INPUT)),
        ]
        assert _as_events(skill_usage.extract_cursor([], tools)) == [
            ("niko", "agent"),
        ]

    def test_read_non_skill_path_yields_nothing(self) -> None:
        """Cursor Read of ordinary source files emits no skill event."""
        tools: list[skill_usage.ToolRow] = [
            ("cursor", "Read", {"path": "src/utils.py"}),
            ("cursor", "Read", {"path": "/home/user/project/README.md"}),
        ]
        assert skill_usage.extract_cursor([], tools) == []

    def test_read_uses_path_key(self) -> None:
        """Extractor reads $.path (Cursor shape); ignores absent file_path."""
        tools: list[skill_usage.ToolRow] = [
            (
                "cursor",
                "Read",
                {"path": "/home/user/.cursor/skills/sr-query/SKILL.md"},
            ),
        ]
        assert _as_events(skill_usage.extract_cursor([], tools)) == [
            ("sr-query", "agent"),
        ]

    def test_read_accepts_file_path_key(self) -> None:
        """Extractor also accepts $.file_path when path is absent."""
        tools: list[skill_usage.ToolRow] = [
            (
                "cursor",
                "Read",
                {"file_path": "/home/user/.cursor/skills/shared/niko/SKILL.md"},
            ),
        ]
        assert _as_events(skill_usage.extract_cursor([], tools)) == [
            ("niko", "agent"),
        ]

    def test_plain_user_messages_are_noop(self) -> None:
        """Ordinary Cursor user text without attachment markup is ignored."""
        messages: list[skill_usage.MessageRow] = [
            ("cursor", CLAUDE_COMMAND_NAME_TEXT),
            ("cursor", "please run /niko"),
        ]
        assert skill_usage.extract_cursor(messages, []) == []

    def test_manually_attached_skills_yield_user_events(self) -> None:
        """Cursor <manually_attached_skills> Skill Name lines → (skill, user)."""
        messages: list[skill_usage.MessageRow] = [
            ("cursor", CURSOR_MANUALLY_ATTACHED_TEXT),
        ]
        assert _as_events(skill_usage.extract_cursor(messages, [])) == [
            ("niko-build", "user"),
        ]

    def test_manually_attached_multiple_skills_all_count(self) -> None:
        """Each Skill Name line in one attachment block is a discrete use."""
        messages: list[skill_usage.MessageRow] = [
            ("cursor", CURSOR_MANUALLY_ATTACHED_MULTI_TEXT),
        ]
        assert _as_events(skill_usage.extract_cursor(messages, [])) == [
            ("niko-archive", "user"),
            ("sr-query", "user"),
        ]


class TestIterSkillUses:
    """Registry dispatch: known harnesses extract; unknown → empty."""

    def test_unknown_harness_yields_empty(self) -> None:
        """iter_skill_uses for an unregistered harness returns no events."""
        messages: list[skill_usage.MessageRow] = [
            ("gemini", CLAUDE_COMMAND_NAME_TEXT),
        ]
        tools: list[skill_usage.ToolRow] = [
            ("gemini", "Skill", {"skill": "niko"}),
        ]
        assert list(skill_usage.iter_skill_uses("gemini", messages, tools)) == []

    def test_extractors_registry_contains_claude_and_cursor(self) -> None:
        """EXTRACTORS maps claude and cursor to their extract functions."""
        assert set(skill_usage.EXTRACTORS) == {"claude", "cursor"}
        assert skill_usage.EXTRACTORS["claude"] is skill_usage.extract_claude
        assert skill_usage.EXTRACTORS["cursor"] is skill_usage.extract_cursor


# --- metrics.skills integration tests -------------------------------------


class TestMetricsSkills:
    """End-to-end skills() ranking, windowing, and response shape."""

    def test_ranks_skills_by_total_with_name_tiebreak(
        self, migrated_con: duckdb.DuckDBPyConnection
    ) -> None:
        """Skills rank by total count across harnesses/invokers; ties by name."""
        _seed_session(
            migrated_con,
            harness="claude",
            session_id="a1",
            activity=datetime(2026, 1, 10),
            started_at=datetime(2026, 1, 10),
            message_count=2,
        )
        migrated_con.execute(
            "UPDATE messages SET text = ? WHERE session_id = 'a1' AND ordinal = 0",
            [CLAUDE_COMMAND_NAME_TEXT],  # niko user
        )
        _seed_tool(
            migrated_con,
            harness="claude",
            session_id="a1",
            message_ordinal=1,
            ordinal=0,
            tool_name="Skill",
            tool_input={"skill": "alpha"},
        )
        _seed_tool(
            migrated_con,
            harness="claude",
            session_id="a1",
            message_ordinal=1,
            ordinal=1,
            tool_name="Skill",
            tool_input={"skill": "alpha"},
        )
        # beta and gamma tied at 1; alpha at 2; niko at 1 → alpha, then beta, gamma, niko
        _seed_tool(
            migrated_con,
            harness="claude",
            session_id="a1",
            message_ordinal=1,
            ordinal=2,
            tool_name="Skill",
            tool_input={"skill": "beta"},
        )
        _seed_tool(
            migrated_con,
            harness="claude",
            session_id="a1",
            message_ordinal=1,
            ordinal=3,
            tool_name="Skill",
            tool_input={"skill": "gamma"},
        )

        result = metrics.skills(
            migrated_con,
            since=datetime(2026, 1, 1),
            until=datetime(2026, 2, 1),
        )
        assert result["skills"] == ["alpha", "beta", "gamma", "niko"]

    def test_respects_limit(self, migrated_con: duckdb.DuckDBPyConnection) -> None:
        """limit caps the ranked skills list."""
        _seed_session(
            migrated_con,
            harness="claude",
            session_id="a1",
            activity=datetime(2026, 1, 10),
            started_at=datetime(2026, 1, 10),
            message_count=2,
        )
        for index, name in enumerate(["z", "y", "x"]):
            _seed_tool(
                migrated_con,
                harness="claude",
                session_id="a1",
                message_ordinal=1,
                ordinal=index,
                tool_name="Skill",
                tool_input={"skill": name},
            )
        result = metrics.skills(
            migrated_con,
            since=datetime(2026, 1, 1),
            until=datetime(2026, 2, 1),
            limit=2,
        )
        assert result["skills"] == ["x", "y"]

    def test_window_and_harness_filter_exclude_subagents(
        self, migrated_con: duckdb.DuckDBPyConnection
    ) -> None:
        """Outside-window and subagent sessions do not contribute events."""
        _seed_session(
            migrated_con,
            harness="claude",
            session_id="in-window",
            activity=datetime(2026, 1, 10),
            started_at=datetime(2026, 1, 10),
            message_count=2,
        )
        _seed_tool(
            migrated_con,
            harness="claude",
            session_id="in-window",
            message_ordinal=1,
            ordinal=0,
            tool_name="Skill",
            tool_input={"skill": "keep"},
        )
        _seed_session(
            migrated_con,
            harness="claude",
            session_id="out-window",
            activity=datetime(2025, 6, 1),
            started_at=datetime(2025, 6, 1),
            message_count=2,
        )
        _seed_tool(
            migrated_con,
            harness="claude",
            session_id="out-window",
            message_ordinal=1,
            ordinal=0,
            tool_name="Skill",
            tool_input={"skill": "drop-window"},
        )
        _seed_session(
            migrated_con,
            harness="cursor",
            session_id="other-harness",
            activity=datetime(2026, 1, 12),
            message_count=2,
        )
        _seed_tool(
            migrated_con,
            harness="cursor",
            session_id="other-harness",
            message_ordinal=1,
            ordinal=0,
            tool_name="Read",
            tool_input={"path": "/skills/drop-harness/SKILL.md"},
        )
        _seed_session(
            migrated_con,
            harness="claude",
            session_id="sub",
            activity=datetime(2026, 1, 11),
            started_at=datetime(2026, 1, 11),
            message_count=2,
        )
        migrated_con.execute(
            "UPDATE sessions SET is_subagent = true WHERE session_id = 'sub'"
        )
        _seed_tool(
            migrated_con,
            harness="claude",
            session_id="sub",
            message_ordinal=1,
            ordinal=0,
            tool_name="Skill",
            tool_input={"skill": "drop-sub"},
        )

        result = metrics.skills(
            migrated_con,
            harnesses=["claude"],
            since=datetime(2026, 1, 1),
            until=datetime(2026, 2, 1),
        )
        assert result["skills"] == ["keep"]
        assert result["calls"] == {
            "claude": {"user": [0], "agent": [1]},
        }

    def test_response_shape_aligned_calls(
        self, migrated_con: duckdb.DuckDBPyConnection
    ) -> None:
        """calls[harness][invoker] arrays align to skills; invokers fixed."""
        _seed_session(
            migrated_con,
            harness="claude",
            session_id="a1",
            activity=datetime(2026, 1, 10),
            started_at=datetime(2026, 1, 10),
            message_count=2,
        )
        migrated_con.execute(
            "UPDATE messages SET text = ? WHERE session_id = 'a1' AND ordinal = 0",
            [CLAUDE_COMMAND_NAME_TEXT],
        )
        _seed_tool(
            migrated_con,
            harness="claude",
            session_id="a1",
            message_ordinal=1,
            ordinal=0,
            tool_name="Skill",
            tool_input={"skill": "niko"},
        )
        _seed_session(
            migrated_con,
            harness="cursor",
            session_id="c1",
            activity=datetime(2026, 1, 11),
            message_count=2,
        )
        _seed_tool(
            migrated_con,
            harness="cursor",
            session_id="c1",
            message_ordinal=1,
            ordinal=0,
            tool_name="Read",
            tool_input=json.loads(CURSOR_SKILL_MD_READ_INPUT),
        )

        result = metrics.skills(
            migrated_con,
            since=datetime(2026, 1, 1),
            until=datetime(2026, 2, 1),
        )
        assert result["invokers"] == ["user", "agent"]
        assert result["skills"] == ["niko"]
        assert result["calls"] == {
            "claude": {"user": [1], "agent": [1]},
            "cursor": {"user": [0], "agent": [1]},
        }

    def test_empty_window_returns_empty_skills(
        self, migrated_con: duckdb.DuckDBPyConnection
    ) -> None:
        """No matching events → empty skills and empty/zero series."""
        _seed_session(
            migrated_con,
            harness="cursor",
            session_id="c1",
            activity=datetime(2026, 1, 10),
        )
        result = metrics.skills(
            migrated_con,
            since=datetime(2026, 1, 1),
            until=datetime(2026, 2, 1),
        )
        assert result["skills"] == []
        assert result["invokers"] == ["user", "agent"]
        assert result["calls"] == {
            "cursor": {"user": [], "agent": []},
        }

    def test_cursor_manually_attached_counts_as_user(
        self, migrated_con: duckdb.DuckDBPyConnection
    ) -> None:
        """Cursor manually_attached_skills in-window contribute user series."""
        _seed_session(
            migrated_con,
            harness="cursor",
            session_id="c-attach",
            activity=datetime(2026, 1, 12),
        )
        migrated_con.execute(
            "UPDATE messages SET text = ? "
            "WHERE session_id = 'c-attach' AND ordinal = 0",
            [CURSOR_MANUALLY_ATTACHED_TEXT],
        )
        result = metrics.skills(
            migrated_con,
            since=datetime(2026, 1, 1),
            until=datetime(2026, 2, 1),
        )
        assert result["skills"] == ["niko-build"]
        assert result["calls"] == {
            "cursor": {"user": [1], "agent": [0]},
        }

    def test_builtin_exit_command_not_in_skills_payload(
        self, migrated_con: duckdb.DuckDBPyConnection
    ) -> None:
        """Claude /exit messages do not appear in the ranked skills list."""
        _seed_session(
            migrated_con,
            harness="claude",
            session_id="a-exit",
            activity=datetime(2026, 1, 10),
            started_at=datetime(2026, 1, 10),
        )
        migrated_con.execute(
            "UPDATE messages SET text = ? WHERE session_id = 'a-exit' AND ordinal = 0",
            [CLAUDE_BUILTIN_EXIT_TEXT],
        )
        result = metrics.skills(
            migrated_con,
            since=datetime(2026, 1, 1),
            until=datetime(2026, 2, 1),
        )
        assert result["skills"] == []

    def test_mix_claude_user_agent_and_cursor_agent(
        self, migrated_con: duckdb.DuckDBPyConnection
    ) -> None:
        """Claude user+agent and Cursor agent aggregate into one payload."""
        _seed_session(
            migrated_con,
            harness="claude",
            session_id="a1",
            activity=datetime(2026, 1, 10),
            started_at=datetime(2026, 1, 10),
            message_count=2,
        )
        migrated_con.execute(
            "UPDATE messages SET text = ? WHERE session_id = 'a1' AND ordinal = 0",
            [CLAUDE_COMMAND_NAME_TEXT],
        )
        _seed_tool(
            migrated_con,
            harness="claude",
            session_id="a1",
            message_ordinal=1,
            ordinal=0,
            tool_name="Skill",
            tool_input={"skill": "gm"},
        )
        # skill blob must not count
        _seed_session(
            migrated_con,
            harness="claude",
            session_id="a2",
            activity=datetime(2026, 1, 11),
            started_at=datetime(2026, 1, 11),
        )
        migrated_con.execute(
            "UPDATE messages SET text = ? WHERE session_id = 'a2' AND ordinal = 0",
            [CLAUDE_SKILL_BLOB_TEXT],
        )
        _seed_session(
            migrated_con,
            harness="cursor",
            session_id="c1",
            activity=datetime(2026, 1, 12),
            message_count=2,
        )
        _seed_tool(
            migrated_con,
            harness="cursor",
            session_id="c1",
            message_ordinal=1,
            ordinal=0,
            tool_name="Read",
            tool_input={"path": "/home/user/.cursor/skills/sr-query/SKILL.md"},
        )
        _seed_tool(
            migrated_con,
            harness="cursor",
            session_id="c1",
            message_ordinal=1,
            ordinal=1,
            tool_name="Read",
            tool_input={"path": "/home/user/.cursor/skills/shared/niko/SKILL.md"},
        )

        result = metrics.skills(
            migrated_con,
            since=datetime(2026, 1, 1),
            until=datetime(2026, 2, 1),
        )
        # niko: claude user + cursor agent = 2; gm and sr-query tied at 1
        assert result["skills"] == ["niko", "gm", "sr-query"]
        assert result["calls"] == {
            "claude": {"user": [1, 0, 0], "agent": [0, 1, 0]},
            "cursor": {"user": [0, 0, 0], "agent": [1, 0, 1]},
        }
