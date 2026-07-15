"""Unit contracts for mode-agnostic dashboard metric payloads."""

import json
from datetime import datetime, timedelta

import duckdb
import pytest

from stockroom.dashboard import metrics


def _seed_session(
    con: duckdb.DuckDBPyConnection,
    *,
    harness: str,
    session_id: str,
    activity: datetime,
    project_id: str,
    message_count: int = 1,
    started_at: datetime | None = None,
    cwd: str | None = None,
    workspace_key: str | None = None,
) -> None:
    """Insert one main session and a deterministic run of messages."""
    con.execute(
        "INSERT INTO sessions "
        "(harness, session_id, project_id, cwd, workspace_key, source_path, "
        "is_subagent, started_at, source_mtime) "
        "VALUES (?, ?, ?, ?, ?, ?, false, ?, ?)",
        [
            harness,
            session_id,
            project_id,
            cwd,
            workspace_key,
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


def _seed_overview_data(con: duckdb.DuckDBPyConnection) -> None:
    _seed_session(
        con,
        harness="cursor",
        session_id="c-current",
        activity=datetime(2026, 1, 10, 8),
        project_id="shared",
        message_count=2,
    )
    _seed_session(
        con,
        harness="claude",
        session_id="a-current",
        activity=datetime(2026, 1, 12, 9),
        started_at=datetime(2026, 1, 12, 9),
        project_id="shared",
        message_count=3,
    )
    _seed_session(
        con,
        harness="cursor",
        session_id="c-prev",
        activity=datetime(2026, 1, 5, 10),
        project_id="previous",
    )
    _seed_session(
        con,
        harness="gemini",
        session_id="g-old",
        activity=datetime(2025, 1, 1),
        project_id="old",
    )
    con.execute(
        "INSERT INTO _sync_state "
        "(harness, source_root, updated_at) VALUES "
        "('cursor', '/cursor', TIMESTAMP '2026-01-15 03:04:05')"
    )


def test_parse_window_accepts_iso_dates_and_uses_exclusive_until() -> None:
    """Dates parse at midnight and preserve the inclusive/exclusive contract."""
    since, until = metrics.parse_window(
        "2026-01-10", "2026-01-12T12:30:00", default_days=30
    )
    assert since == datetime(2026, 1, 10)
    assert until == datetime(2026, 1, 12, 12, 30)


def test_parse_window_applies_default_and_rejects_reversed_bounds() -> None:
    """A missing since uses the default duration; reversed windows are invalid."""
    now = datetime(2026, 2, 1, 12)
    since, until = metrics.parse_window(None, None, default_days=14, now=now)
    assert since == datetime(2026, 1, 18, 12)
    assert until == now
    with pytest.raises(ValueError, match="since"):
        metrics.parse_window("2026-02-02", "2026-02-01", default_days=14)


def test_parse_window_default_now_is_utc(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When ``now`` is omitted, the window end comes from ``utc_now``."""
    frozen = datetime(2026, 7, 10, 3, 22, 0)
    monkeypatch.setattr(metrics, "utc_now", lambda: frozen)
    since, until = metrics.parse_window(None, None, default_days=1)
    assert until == frozen
    assert since == datetime(2026, 7, 9, 3, 22, 0)


def test_empty_overview_has_stable_zero_shape(
    migrated_con: duckdb.DuckDBPyConnection,
) -> None:
    """A migrated but un-ingested warehouse returns a complete empty payload."""
    assert metrics.overview(
        migrated_con,
        since=datetime(2026, 1, 1),
        until=datetime(2026, 2, 1),
    ) == {
        "last_sync": None,
        "per_harness": {},
        "distinct_projects": 0,
        "prev_distinct_projects": 0,
    }


def test_trends_defaults_to_fourteen_days_and_twelve_calendar_weeks(
    migrated_con: duckdb.DuckDBPyConnection,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Default trend windows expose exactly 14 day and 12 week labels."""
    monkeypatch.setattr(metrics, "utc_now", lambda: datetime(2026, 2, 1, 12))
    result = metrics.trends(migrated_con)
    assert result["daily"]["granularity"] == "day"
    assert result["daily"]["labels"] == [
        f"2026-01-{day:02d}" for day in range(19, 32)
    ] + ["2026-02-01"]
    assert result["weekly"]["granularity"] == "week"
    assert len(result["weekly"]["labels"]) == 12
    assert result["weekly"]["labels"][0] == "2025-11-10"
    assert result["weekly"]["labels"][-1] == "2026-01-26"


def test_trends_bounded_window_uses_shared_adaptive_granularity(
    migrated_con: duckdb.DuckDBPyConnection,
) -> None:
    """Range picker windows share one bucket size across both time-series panels."""
    _seed_session(
        migrated_con,
        harness="cursor",
        session_id="c-day",
        activity=datetime(2026, 1, 10, 8),
        project_id="p",
    )
    _seed_tool(
        migrated_con,
        harness="cursor",
        session_id="c-day",
        ordinal=0,
        tool_name="ReadFile",
    )

    seven_day = metrics.trends(
        migrated_con,
        since=datetime(2026, 1, 10),
        until=datetime(2026, 1, 17),
    )
    assert seven_day["daily"]["granularity"] == "day"
    assert seven_day["weekly"]["granularity"] == "day"
    assert seven_day["daily"]["labels"] == seven_day["weekly"]["labels"]
    assert len(seven_day["daily"]["labels"]) == 7

    thirty_day = metrics.trends(
        migrated_con,
        since=datetime(2026, 1, 1),
        until=datetime(2026, 1, 31),
    )
    assert thirty_day["daily"]["granularity"] == "day"
    assert thirty_day["weekly"]["granularity"] == "day"
    assert thirty_day["daily"]["labels"] == thirty_day["weekly"]["labels"]
    assert len(thirty_day["daily"]["labels"]) == 30

    sixty_day = metrics.trends(
        migrated_con,
        since=datetime(2026, 1, 1),
        until=datetime(2026, 3, 2),
    )
    assert sixty_day["daily"]["granularity"] == "week"
    assert sixty_day["weekly"]["granularity"] == "week"
    assert sixty_day["daily"]["labels"] == sixty_day["weekly"]["labels"]
    assert len(sixty_day["daily"]["labels"]) >= 8

    ninety_day = metrics.trends(
        migrated_con,
        since=datetime(2026, 1, 1),
        until=datetime(2026, 4, 1),
    )
    assert ninety_day["daily"]["granularity"] == "week"
    assert ninety_day["weekly"]["granularity"] == "week"
    assert ninety_day["daily"]["labels"] == ninety_day["weekly"]["labels"]

    year = metrics.trends(
        migrated_con,
        since=datetime(2025, 1, 1),
        until=datetime(2026, 1, 1),
    )
    assert year["daily"]["granularity"] == "month"
    assert year["weekly"]["granularity"] == "month"
    assert year["daily"]["labels"] == year["weekly"]["labels"]
    assert year["daily"]["labels"][0] == "2025-01-01"
    assert year["daily"]["labels"][-1] == "2025-12-01"


def test_overview_returns_per_harness_counts_previous_window_and_rollups(
    migrated_con: duckdb.DuckDBPyConnection,
) -> None:
    """Overview counts current/previous KPIs and distinct projects correctly."""
    _seed_overview_data(migrated_con)
    result = metrics.overview(
        migrated_con,
        since=datetime(2026, 1, 10),
        until=datetime(2026, 1, 20),
    )
    assert result == {
        "last_sync": "2026-01-15T03:04:05Z",
        "per_harness": {
            "claude": {
                "sessions": 1,
                "messages": 3,
                "projects": 1,
                "prev_sessions": 0,
                "prev_messages": 0,
                "prev_projects": 0,
            },
            "cursor": {
                "sessions": 1,
                "messages": 2,
                "projects": 1,
                "prev_sessions": 1,
                "prev_messages": 1,
                "prev_projects": 1,
            },
            "gemini": {
                "sessions": 0,
                "messages": 0,
                "projects": 0,
                "prev_sessions": 0,
                "prev_messages": 0,
                "prev_projects": 0,
            },
        },
        "distinct_projects": 1,
        "prev_distinct_projects": 1,
    }


def test_overview_prev_distinct_projects_unions_shared_previous_projects(
    migrated_con: duckdb.DuckDBPyConnection,
) -> None:
    """Previous distinct is a union; shared projects must not inflate the rollup."""
    _seed_overview_data(migrated_con)
    _seed_session(
        migrated_con,
        harness="claude",
        session_id="a-prev-shared",
        activity=datetime(2026, 1, 6, 11),
        started_at=datetime(2026, 1, 6, 11),
        project_id="previous",
        message_count=1,
    )
    result = metrics.overview(
        migrated_con,
        since=datetime(2026, 1, 10),
        until=datetime(2026, 1, 20),
    )
    prev_sum = sum(values["prev_projects"] for values in result["per_harness"].values())
    assert result["per_harness"]["cursor"]["prev_projects"] == 1
    assert result["per_harness"]["claude"]["prev_projects"] == 1
    assert prev_sum == 2
    assert result["prev_distinct_projects"] == 1
    assert result["prev_distinct_projects"] < prev_sum


def test_overview_filter_and_unknown_harness_are_mode_agnostic(
    migrated_con: duckdb.DuckDBPyConnection,
) -> None:
    """Repeated selection narrows keys; unknown harnesses return a zero shape."""
    _seed_overview_data(migrated_con)
    window = {
        "since": datetime(2026, 1, 10),
        "until": datetime(2026, 1, 20),
    }
    selected = metrics.overview(migrated_con, ["cursor"], **window)
    assert list(selected["per_harness"]) == ["cursor"]
    assert selected["distinct_projects"] == 1
    assert selected["prev_distinct_projects"] == 1

    unknown = metrics.overview(migrated_con, ["missing"], **window)
    assert list(unknown["per_harness"]) == ["missing"]
    assert unknown["per_harness"]["missing"]["sessions"] == 0
    assert unknown["distinct_projects"] == 0
    assert unknown["prev_distinct_projects"] == 0


def test_trends_zero_fills_daily_and_classifies_weekly_tools(
    migrated_con: duckdb.DuckDBPyConnection,
) -> None:
    """Daily series fill gaps; only configured tool names enter read/write."""
    _seed_session(
        migrated_con,
        harness="cursor",
        session_id="c1",
        activity=datetime(2026, 1, 10, 8),
        project_id="p",
    )
    _seed_session(
        migrated_con,
        harness="claude",
        session_id="a1",
        activity=datetime(2026, 1, 12, 9),
        started_at=datetime(2026, 1, 12, 9),
        project_id="p",
    )
    _seed_tool(
        migrated_con,
        harness="cursor",
        session_id="c1",
        ordinal=0,
        tool_name="Write",
    )
    _seed_tool(
        migrated_con,
        harness="cursor",
        session_id="c1",
        ordinal=1,
        tool_name="ReadFile",
    )
    _seed_tool(
        migrated_con,
        harness="cursor",
        session_id="c1",
        ordinal=2,
        tool_name="Shell",
    )
    _seed_tool(
        migrated_con,
        harness="claude",
        session_id="a1",
        ordinal=0,
        tool_name="ApplyPatch",
    )

    result = metrics.trends(
        migrated_con,
        since=datetime(2026, 1, 10),
        until=datetime(2026, 1, 13),
    )
    assert result == {
        "daily": {
            "granularity": "day",
            "labels": ["2026-01-10", "2026-01-11", "2026-01-12"],
            "sessions": {"claude": [0, 0, 1], "cursor": [1, 0, 0]},
        },
        "weekly": {
            "granularity": "day",
            "labels": ["2026-01-10", "2026-01-11", "2026-01-12"],
            "writes": {"claude": [0, 0, 1], "cursor": [1, 0, 0]},
            "reads": {"claude": [0, 0, 0], "cursor": [1, 0, 0]},
        },
    }


def test_window_edges_source_mtime_and_subagents_are_cross_cutting(
    migrated_con: duckdb.DuckDBPyConnection,
) -> None:
    """Windows are [since, until), Cursor uses mtime, and subagents stay excluded."""
    _seed_session(
        migrated_con,
        harness="cursor",
        session_id="at-since",
        activity=datetime(2026, 1, 10),
        project_id="p",
    )
    _seed_session(
        migrated_con,
        harness="cursor",
        session_id="before-until",
        activity=datetime(2026, 1, 19, 23, 59, 59),
        project_id="p",
    )
    _seed_session(
        migrated_con,
        harness="cursor",
        session_id="at-until",
        activity=datetime(2026, 1, 20),
        project_id="p",
    )
    _seed_session(
        migrated_con,
        harness="cursor",
        session_id="subagent",
        activity=datetime(2026, 1, 15),
        project_id="p",
    )
    migrated_con.execute(
        "UPDATE sessions SET is_subagent = true WHERE session_id = 'subagent'"
    )
    _seed_tool(
        migrated_con,
        harness="cursor",
        session_id="at-since",
        ordinal=0,
        tool_name="Read",
    )
    _seed_tool(
        migrated_con,
        harness="cursor",
        session_id="subagent",
        ordinal=0,
        tool_name="Write",
    )
    window = {
        "since": datetime(2026, 1, 10),
        "until": datetime(2026, 1, 20),
    }

    overview = metrics.overview(migrated_con, **window)
    assert overview["per_harness"]["cursor"]["sessions"] == 2
    trends = metrics.trends(migrated_con, **window)
    assert sum(trends["daily"]["sessions"]["cursor"]) == 2
    assert sum(trends["weekly"]["reads"]["cursor"]) == 1
    assert sum(trends["weekly"]["writes"]["cursor"]) == 0
    assert metrics.tools(migrated_con, **window) == {
        "tools": ["Read"],
        "calls": {"cursor": [1]},
    }
    assert sum(metrics.efficiency(migrated_con, **window)["sessions"]["cursor"]) == 2
    assert metrics.wrapped(migrated_con)["totals"]["sessions"] == 3


def test_projects_ranks_by_selected_total_with_aligned_harness_counts(
    migrated_con: duckdb.DuckDBPyConnection,
) -> None:
    """Projects rank deterministically and each harness gets aligned counts."""
    for harness, session_id, project in [
        ("cursor", "c-pa-1", "pa"),
        ("cursor", "c-pa-2", "pa"),
        ("claude", "a-pa", "pa"),
        ("claude", "a-pb-1", "pb"),
        ("claude", "a-pb-2", "pb"),
        ("cursor", "c-pc", "pc"),
    ]:
        _seed_session(
            migrated_con,
            harness=harness,
            session_id=session_id,
            activity=datetime(2026, 1, 10),
            project_id=project,
        )

    result = metrics.projects(
        migrated_con,
        since=datetime(2026, 1, 1),
        until=datetime(2026, 2, 1),
        limit=2,
    )
    assert result == {
        "projects": ["pa", "pb"],
        "labels": ["pa", "pb"],
        "sessions": {"claude": [1, 2], "cursor": [2, 0]},
    }

    selected = metrics.projects(
        migrated_con,
        ["cursor"],
        since=datetime(2026, 1, 1),
        until=datetime(2026, 2, 1),
        limit=2,
    )
    assert selected == {
        "projects": ["pa", "pc"],
        "labels": ["pa", "pc"],
        "sessions": {"cursor": [2, 1]},
    }


def test_projects_labels_use_unique_cwd_basename(
    migrated_con: duckdb.DuckDBPyConnection,
) -> None:
    """When all non-NULL cwds share one leaf, labels use that basename."""
    _seed_session(
        migrated_con,
        harness="cursor",
        session_id="c1",
        activity=datetime(2026, 1, 10),
        project_id="home-me-stockroom",
        cwd="/home/me/stockroom",
    )
    _seed_session(
        migrated_con,
        harness="claude",
        session_id="a1",
        activity=datetime(2026, 1, 11),
        project_id="home-me-stockroom",
        cwd="/home/me/stockroom",
    )
    result = metrics.projects(
        migrated_con,
        since=datetime(2026, 1, 1),
        until=datetime(2026, 2, 1),
    )
    assert result["projects"] == ["home-me-stockroom"]
    assert result["labels"] == ["stockroom"]


def test_projects_labels_fall_back_to_id_when_short_names_disagree(
    migrated_con: duckdb.DuckDBPyConnection,
) -> None:
    """Disagreeing cwd basenames for one project_id → label is the full id."""
    _seed_session(
        migrated_con,
        harness="cursor",
        session_id="c1",
        activity=datetime(2026, 1, 12),
        project_id="ambiguous-slug",
        cwd="/home/me/stockroom",
    )
    _seed_session(
        migrated_con,
        harness="claude",
        session_id="a1",
        activity=datetime(2026, 1, 11),
        project_id="ambiguous-slug",
        cwd="/tmp/other-checkout",
    )
    result = metrics.projects(
        migrated_con,
        since=datetime(2026, 1, 1),
        until=datetime(2026, 2, 1),
    )
    assert result["projects"] == ["ambiguous-slug"]
    assert result["labels"] == ["ambiguous-slug"]


def test_projects_ranking_stays_by_key_when_basenames_collide(
    migrated_con: duckdb.DuckDBPyConnection,
) -> None:
    """Same leaf, different cwds → distinct workspace_keys; labels may collide."""
    _seed_session(
        migrated_con,
        harness="cursor",
        session_id="c1",
        activity=datetime(2026, 1, 10),
        project_id="path-a-stockroom",
        cwd="/path/a/stockroom",
        workspace_key="path-a-stockroom",
        message_count=1,
    )
    _seed_session(
        migrated_con,
        harness="cursor",
        session_id="c2",
        activity=datetime(2026, 1, 10),
        project_id="path-a-stockroom",
        cwd="/path/a/stockroom",
        workspace_key="path-a-stockroom",
    )
    _seed_session(
        migrated_con,
        harness="claude",
        session_id="a1",
        activity=datetime(2026, 1, 10),
        project_id="path-b-stockroom",
        cwd="/path/b/stockroom",
        workspace_key="path-b-stockroom",
    )
    result = metrics.projects(
        migrated_con,
        since=datetime(2026, 1, 1),
        until=datetime(2026, 2, 1),
    )
    assert result["projects"] == ["path-a-stockroom", "path-b-stockroom"]
    assert result["labels"] == ["stockroom", "stockroom"]
    assert result["sessions"] == {"claude": [0, 1], "cursor": [2, 0]}


def test_projects_merges_same_cwd_across_harnesses(
    migrated_con: duckdb.DuckDBPyConnection,
) -> None:
    """Different project_ids, same cwd/workspace_key → one ranked rollup key."""
    _seed_session(
        migrated_con,
        harness="cursor",
        session_id="c1",
        activity=datetime(2026, 1, 10),
        project_id="home-me-stockroom",
        cwd="/home/me/stockroom",
        workspace_key="home-me-stockroom",
    )
    _seed_session(
        migrated_con,
        harness="claude",
        session_id="a1",
        activity=datetime(2026, 1, 11),
        project_id="-home-me-stockroom",
        cwd="/home/me/stockroom",
        workspace_key="home-me-stockroom",
    )
    _seed_session(
        migrated_con,
        harness="cursor",
        session_id="c2",
        activity=datetime(2026, 1, 12),
        project_id="home-me-other",
        cwd="/home/me/other",
        workspace_key="home-me-other",
    )
    result = metrics.projects(
        migrated_con,
        since=datetime(2026, 1, 1),
        until=datetime(2026, 2, 1),
    )
    assert result["projects"] == ["home-me-stockroom", "home-me-other"]
    assert result["labels"] == ["stockroom", "other"]
    assert result["sessions"] == {"claude": [1, 0], "cursor": [1, 1]}


def test_projects_falls_back_to_project_id_when_workspace_key_null(
    migrated_con: duckdb.DuckDBPyConnection,
) -> None:
    """NULL workspace_key still groups via coalesce to project_id."""
    _seed_session(
        migrated_con,
        harness="cursor",
        session_id="c1",
        activity=datetime(2026, 1, 10),
        project_id="orphan-slug",
        cwd=None,
        workspace_key=None,
    )
    result = metrics.projects(
        migrated_con,
        since=datetime(2026, 1, 1),
        until=datetime(2026, 2, 1),
    )
    assert result["projects"] == ["orphan-slug"]
    assert result["labels"] == ["orphan-slug"]
    assert result["sessions"] == {"cursor": [1]}


def test_project_display_name_uses_cwd_basename_or_id() -> None:
    """Shared helper: basename when cwd present, else project_id."""
    assert metrics.project_display_name("/home/me/stockroom", "slug") == "stockroom"
    assert metrics.project_display_name(None, "slug") == "slug"
    assert metrics.project_display_name("", "slug") == "slug"


def test_tools_ranks_calls_with_per_harness_breakout(
    migrated_con: duckdb.DuckDBPyConnection,
) -> None:
    """Tool names rank by total selected calls with deterministic ties."""
    for harness, session_id in [("cursor", "c1"), ("claude", "a1")]:
        _seed_session(
            migrated_con,
            harness=harness,
            session_id=session_id,
            activity=datetime(2026, 1, 10),
            project_id="p",
        )
    for harness, session_id, names in [
        ("cursor", "c1", ["Read", "Read", "Shell", "Shell", "Shell"]),
        ("claude", "a1", ["Read", "Write", "Write"]),
    ]:
        for ordinal, name in enumerate(names):
            _seed_tool(
                migrated_con,
                harness=harness,
                session_id=session_id,
                ordinal=ordinal,
                tool_name=name,
            )

    result = metrics.tools(
        migrated_con,
        since=datetime(2026, 1, 1),
        until=datetime(2026, 2, 1),
    )
    assert result == {
        "tools": ["Read", "Shell", "Write"],
        "calls": {"claude": [1, 0, 2], "cursor": [2, 3, 0]},
    }


def test_models_unifies_message_and_session_grains_once_per_session(
    migrated_con: duckdb.DuckDBPyConnection,
) -> None:
    """A model counts once per session across message and session-list grains."""
    _seed_session(
        migrated_con,
        harness="cursor",
        session_id="c1",
        activity=datetime(2026, 1, 10),
        project_id="p",
    )
    _seed_session(
        migrated_con,
        harness="cursor",
        session_id="c2",
        activity=datetime(2026, 1, 11),
        project_id="p",
    )
    migrated_con.execute(
        "UPDATE sessions SET models = ['m1', 'm3'] WHERE session_id = 'c1'"
    )
    migrated_con.execute("UPDATE sessions SET models = ['m1'] WHERE session_id = 'c2'")
    _seed_session(
        migrated_con,
        harness="claude",
        session_id="a1",
        activity=datetime(2026, 1, 12),
        project_id="p",
        message_count=3,
    )
    migrated_con.execute(
        "UPDATE messages SET model = CASE "
        "WHEN ordinal < 2 THEN 'm1' ELSE 'm2' END "
        "WHERE session_id = 'a1'"
    )
    _seed_session(
        migrated_con,
        harness="cursor",
        session_id="sub",
        activity=datetime(2026, 1, 13),
        project_id="p",
    )
    migrated_con.execute(
        "UPDATE sessions SET models = ['m4'], is_subagent = true "
        "WHERE session_id = 'sub'"
    )

    result = metrics.models(
        migrated_con,
        since=datetime(2026, 1, 1),
        until=datetime(2026, 2, 1),
    )
    assert result == {
        "models": ["m1", "m2", "m3"],
        "sessions": {"claude": [1, 1, 0], "cursor": [2, 0, 1]},
    }


def test_efficiency_covers_boundaries_and_weighted_prompt_averages(
    migrated_con: duckdb.DuckDBPyConnection,
) -> None:
    """Message and prompt buckets include every documented boundary."""
    cases = [
        ("s2", 2, 50),
        ("s3", 3, 99),
        ("s10", 10, 100),
        ("s11", 11, 500),
        ("s40", 40, 501),
        ("s41", 41, 600),
    ]
    for session_id, message_count, prompt_length in cases:
        _seed_session(
            migrated_con,
            harness="cursor",
            session_id=session_id,
            activity=datetime(2026, 1, 10),
            project_id="p",
            message_count=message_count,
        )
        migrated_con.execute(
            "UPDATE messages SET text = ? WHERE session_id = ? AND ordinal = 0",
            ["x" * prompt_length, session_id],
        )

    result = metrics.efficiency(
        migrated_con,
        since=datetime(2026, 1, 1),
        until=datetime(2026, 2, 1),
    )
    assert result == {
        "buckets": ["abandoned", "short", "medium", "long"],
        "sessions": {"cursor": [1, 2, 2, 1]},
        "first_prompt": {
            "labels": ["short", "medium", "detailed"],
            "avg_msgs": {"cursor": [2.5, 10.5, 40.5]},
            "n": {"cursor": [2, 2, 2]},
        },
    }


def test_sessions_are_recent_filtered_and_display_truncated(
    migrated_con: duckdb.DuckDBPyConnection,
) -> None:
    """Recent sessions are newest-first with model/project/prompt display fields."""
    _seed_session(
        migrated_con,
        harness="cursor",
        session_id="c-old",
        activity=datetime(2026, 1, 1, 8),
        project_id="cursor-project",
    )
    migrated_con.execute(
        "UPDATE sessions SET models = ['gpt-5'] WHERE session_id = 'c-old'"
    )
    _seed_session(
        migrated_con,
        harness="claude",
        session_id="a-new",
        activity=datetime(2026, 1, 2, 9),
        started_at=datetime(2026, 1, 2, 9),
        project_id="claude-project",
        message_count=3,
    )
    migrated_con.execute(
        "UPDATE sessions SET cwd = '/home/me/stockroom' WHERE session_id = 'a-new'"
    )
    migrated_con.execute(
        "UPDATE messages SET model = CASE "
        "WHEN ordinal < 2 THEN 'claude-sonnet' ELSE 'claude-opus' END "
        "WHERE session_id = 'a-new'"
    )
    migrated_con.execute(
        "UPDATE messages SET text = ? WHERE session_id = 'a-new' AND ordinal = 0",
        ["x" * 130],
    )
    _seed_session(
        migrated_con,
        harness="cursor",
        session_id="sub",
        activity=datetime(2026, 1, 3, 10),
        project_id="ignored",
    )
    migrated_con.execute(
        "UPDATE sessions SET is_subagent = true WHERE session_id = 'sub'"
    )

    result = metrics.sessions(migrated_con, limit=2)
    assert result["total"] == 2
    assert result["sessions"] == [
        {
            "started": "2026-01-02T09:00:00Z",
            "harness": "claude",
            "session_id": "a-new",
            "project_name": "stockroom",
            "project_id": "claude-project",
            "msgs": 3,
            "model": "claude-sonnet",
            "prompt": f"{'x' * 120}…(+10)",
        },
        {
            "started": "2026-01-01T08:00:00Z",
            "harness": "cursor",
            "session_id": "c-old",
            "project_name": "cursor-project",
            "project_id": "cursor-project",
            "msgs": 1,
            "model": "gpt-5",
            "prompt": "message 0",
        },
    ]
    assert [
        row["harness"]
        for row in metrics.sessions(migrated_con, ["cursor"])["sessions"]
    ] == ["cursor"]


def _seed_n_sessions(
    con: duckdb.DuckDBPyConnection,
    n: int,
    *,
    harness: str = "cursor",
    base: datetime | None = None,
) -> list[str]:
    """Seed ``n`` main sessions with distinct activity times; return session_ids oldest→newest."""
    start = base or datetime(2026, 1, 1, 0)
    ids: list[str] = []
    for i in range(n):
        session_id = f"s{i:02d}"
        ids.append(session_id)
        _seed_session(
            con,
            harness=harness,
            session_id=session_id,
            activity=start + timedelta(hours=i),
            project_id="p",
        )
    return ids


def test_sessions_ends_empty_when_no_matching_sessions(
    migrated_con: duckdb.DuckDBPyConnection,
) -> None:
    """Empty filter set returns total 0 with empty newest and oldest lists."""
    result = metrics.sessions_ends(migrated_con)
    assert result == {"total": 0, "newest": [], "oldest": []}


def test_sessions_ends_returns_all_in_newest_when_total_at_most_20(
    migrated_con: duckdb.DuckDBPyConnection,
) -> None:
    """When total ≤ 20, newest holds all DESC and oldest is empty."""
    ids = _seed_n_sessions(migrated_con, 20)
    result = metrics.sessions_ends(migrated_con)
    assert result["total"] == 20
    assert result["oldest"] == []
    assert [row["session_id"] for row in result["newest"]] == list(reversed(ids))
    assert len(result["newest"]) == 20


def test_sessions_ends_splits_newest_and_oldest_when_total_over_20(
    migrated_con: duckdb.DuckDBPyConnection,
) -> None:
    """When total > 20, newest is 10 DESC and oldest is 10 ASC; N = total − 20."""
    ids = _seed_n_sessions(migrated_con, 25)
    result = metrics.sessions_ends(migrated_con)
    assert result["total"] == 25
    assert [row["session_id"] for row in result["newest"]] == list(reversed(ids[-10:]))
    assert [row["session_id"] for row in result["oldest"]] == ids[:10]
    assert len(result["newest"]) == 10
    assert len(result["oldest"]) == 10


def test_sessions_ends_respects_harness_and_activity_window(
    migrated_con: duckdb.DuckDBPyConnection,
) -> None:
    """Harness and since/until filters apply; subagents are excluded."""
    _seed_session(
        migrated_con,
        harness="cursor",
        session_id="in-window",
        activity=datetime(2026, 1, 15, 12),
        project_id="p",
    )
    _seed_session(
        migrated_con,
        harness="claude",
        session_id="other-harness",
        activity=datetime(2026, 1, 15, 13),
        started_at=datetime(2026, 1, 15, 13),
        project_id="p",
    )
    _seed_session(
        migrated_con,
        harness="cursor",
        session_id="too-old",
        activity=datetime(2026, 1, 1, 8),
        project_id="p",
    )
    _seed_session(
        migrated_con,
        harness="cursor",
        session_id="sub",
        activity=datetime(2026, 1, 15, 14),
        project_id="p",
    )
    migrated_con.execute(
        "UPDATE sessions SET is_subagent = true WHERE session_id = 'sub'"
    )

    result = metrics.sessions_ends(
        migrated_con,
        ["cursor"],
        since=datetime(2026, 1, 10),
        until=datetime(2026, 1, 20),
    )
    assert result["total"] == 1
    assert [row["session_id"] for row in result["newest"]] == ["in-window"]
    assert result["oldest"] == []


def test_sessions_ends_row_fields_match_sessions_list_shape(
    migrated_con: duckdb.DuckDBPyConnection,
) -> None:
    """Ends rows use the same display fields as the sessions list path."""
    _seed_session(
        migrated_con,
        harness="claude",
        session_id="a-new",
        activity=datetime(2026, 1, 2, 9),
        started_at=datetime(2026, 1, 2, 9),
        project_id="claude-project",
        message_count=3,
    )
    migrated_con.execute(
        "UPDATE sessions SET cwd = '/home/me/stockroom' WHERE session_id = 'a-new'"
    )
    migrated_con.execute(
        "UPDATE messages SET model = CASE "
        "WHEN ordinal < 2 THEN 'claude-sonnet' ELSE 'claude-opus' END "
        "WHERE session_id = 'a-new'"
    )
    migrated_con.execute(
        "UPDATE messages SET text = ? WHERE session_id = 'a-new' AND ordinal = 0",
        ["x" * 130],
    )

    ends = metrics.sessions_ends(migrated_con)
    listed = metrics.sessions(migrated_con, limit=1)
    assert ends["total"] == 1
    assert ends["newest"] == listed["sessions"]
    assert ends["newest"][0] == {
        "started": "2026-01-02T09:00:00Z",
        "harness": "claude",
        "session_id": "a-new",
        "project_name": "stockroom",
        "project_id": "claude-project",
        "msgs": 3,
        "model": "claude-sonnet",
        "prompt": f"{'x' * 120}…(+10)",
    }


def test_wrapped_returns_all_time_rollups_and_ignores_selector(
    migrated_con: duckdb.DuckDBPyConnection,
) -> None:
    """Wrapped computes totals, streak, marathon, peak, and top tool all-time."""
    for harness, session_id, activity, project_id, message_count in [
        ("cursor", "c1", datetime(2026, 1, 1, 10), "p1", 2),
        ("claude", "a1", datetime(2026, 1, 2, 10), "p1", 5),
        ("claude", "a2", datetime(2026, 1, 3, 14), "p2", 3),
        ("cursor", "c2", datetime(2026, 1, 5, 14), "p3", 1),
    ]:
        _seed_session(
            migrated_con,
            harness=harness,
            session_id=session_id,
            activity=activity,
            project_id=project_id,
            message_count=message_count,
        )
    for ordinal in range(3):
        _seed_tool(
            migrated_con,
            harness="cursor",
            session_id="c1",
            ordinal=ordinal,
            tool_name="Read",
        )
    for ordinal in range(2):
        _seed_tool(
            migrated_con,
            harness="claude",
            session_id="a1",
            ordinal=ordinal,
            tool_name="Write",
        )

    result = metrics.wrapped(
        migrated_con,
        ["cursor"],
        since=datetime(2026, 1, 5),
        until=datetime(2026, 1, 6),
    )
    assert result == {
        "totals": {
            "sessions": 4,
            "messages": 11,
            "span": {"start": "2026-01-01", "end": "2026-01-05", "days": 5},
        },
        "distinct_projects": 3,
        "busiest_harness": {"name": "claude", "pct": 50.0},
        "best_streak": {
            "days": 3,
            "start": "2026-01-01",
            "end": "2026-01-03",
        },
        "marathon_session": {
            "messages": 5,
            "project_name": "p1",
            "project_id": "p1",
            "harness": "claude",
        },
        "peak_hour": {"hour": 10, "count": 2},
        "top_tool": {"name": "Read", "calls": 3},
    }


def test_session_detail_reconstructs_ordered_messages_and_nested_tools(
    migrated_con: duckdb.DuckDBPyConnection,
) -> None:
    """Detail returns full text, ordinal-ordered messages, and nested tool_calls."""
    long_prompt = "x" * 200
    _seed_session(
        migrated_con,
        harness="cursor",
        session_id="detail-1",
        activity=datetime(2026, 1, 5, 12),
        project_id="proj-a",
        message_count=2,
        cwd="/home/me/stockroom",
    )
    migrated_con.execute(
        "UPDATE messages SET text = ?, model = 'gpt-5', ts = ? "
        "WHERE session_id = 'detail-1' AND ordinal = 0",
        [long_prompt, datetime(2026, 1, 5, 12, 0, 1)],
    )
    migrated_con.execute(
        "UPDATE messages SET text = ?, model = 'gpt-5', ts = ? "
        "WHERE session_id = 'detail-1' AND ordinal = 1",
        ["assistant reply", datetime(2026, 1, 5, 12, 0, 2)],
    )
    _seed_tool(
        migrated_con,
        harness="cursor",
        session_id="detail-1",
        message_ordinal=1,
        ordinal=1,
        tool_name="Shell",
        tool_input={"command": "ls"},
    )
    _seed_tool(
        migrated_con,
        harness="cursor",
        session_id="detail-1",
        message_ordinal=1,
        ordinal=0,
        tool_name="Read",
        tool_input={"path": "a.py"},
    )

    result = metrics.session_detail(migrated_con, "cursor", "detail-1")
    assert result is not None
    assert result["harness"] == "cursor"
    assert result["session_id"] == "detail-1"
    assert result["project_id"] == "proj-a"
    assert result["project_name"] == "stockroom"
    assert result["cwd"] == "/home/me/stockroom"
    assert result["started"] == "2026-01-05T12:00:00Z"
    assert result["is_subagent"] is False
    assert result["parent_session_id"] is None
    assert [message["ordinal"] for message in result["messages"]] == [0, 1]
    assert result["messages"][0] == {
        "message_id": "detail-1#0",
        "ordinal": 0,
        "role": "user",
        "text": long_prompt,
        "model": "gpt-5",
        "ts": "2026-01-05T12:00:01Z",
        "tool_calls": [],
    }
    assert "…(+" not in result["messages"][0]["text"]
    assert result["messages"][1]["text"] == "assistant reply"
    assert result["messages"][1]["tool_calls"] == [
        {"ordinal": 0, "tool_name": "Read", "tool_input": {"path": "a.py"}},
        {"ordinal": 1, "tool_name": "Shell", "tool_input": {"command": "ls"}},
    ]


def test_session_detail_missing_session_returns_none(
    migrated_con: duckdb.DuckDBPyConnection,
) -> None:
    """Unknown (harness, session_id) yields None for the server to map to 404."""
    assert metrics.session_detail(migrated_con, "cursor", "missing") is None


def test_session_detail_serves_subagent_when_addressed_directly(
    migrated_con: duckdb.DuckDBPyConnection,
) -> None:
    """Subagent sessions are excluded from the list but available by detail id."""
    _seed_session(
        migrated_con,
        harness="claude",
        session_id="parent",
        activity=datetime(2026, 1, 4, 8),
        project_id="p",
    )
    _seed_session(
        migrated_con,
        harness="claude",
        session_id="child",
        activity=datetime(2026, 1, 4, 9),
        project_id="p",
        message_count=1,
    )
    migrated_con.execute(
        "UPDATE sessions SET is_subagent = true, parent_session_id = 'parent' "
        "WHERE session_id = 'child'"
    )

    result = metrics.session_detail(migrated_con, "claude", "child")
    assert result is not None
    assert result["is_subagent"] is True
    assert result["parent_session_id"] == "parent"
    assert len(result["messages"]) == 1
    assert "child" not in {
        row["session_id"]
        for row in metrics.sessions(migrated_con, limit=50)["sessions"]
    }


def test_sessions_envelope_supports_offset_order_and_show_all(
    migrated_con: duckdb.DuckDBPyConnection,
) -> None:
    """Paged sessions return {total, sessions} with offset/order; limit=0 is show-all."""
    ids = _seed_n_sessions(migrated_con, 5)
    page = metrics.sessions(migrated_con, limit=2, offset=1, order="desc")
    assert page["total"] == 5
    assert [row["session_id"] for row in page["sessions"]] == list(reversed(ids))[1:3]

    asc = metrics.sessions(migrated_con, limit=2, offset=0, order="asc")
    assert [row["session_id"] for row in asc["sessions"]] == ids[:2]

    all_rows = metrics.sessions(migrated_con, limit=0)
    assert all_rows["total"] == 5
    assert [row["session_id"] for row in all_rows["sessions"]] == list(reversed(ids))


def test_sessions_envelope_empty_when_no_harnesses(
    migrated_con: duckdb.DuckDBPyConnection,
) -> None:
    """No matching harnesses yields total 0 and an empty sessions list."""
    result = metrics.sessions(migrated_con, ["missing-harness"], limit=10)
    assert result == {"total": 0, "sessions": []}
