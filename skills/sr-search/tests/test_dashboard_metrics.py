"""Unit contracts for mode-agnostic dashboard metric payloads."""

from datetime import datetime

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
) -> None:
    """Insert one main session and a deterministic run of messages."""
    con.execute(
        "INSERT INTO sessions "
        "(harness, session_id, project_id, source_path, is_subagent, "
        "started_at, source_mtime) VALUES (?, ?, ?, ?, false, ?, ?)",
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
) -> None:
    con.execute(
        "INSERT INTO tool_calls "
        "(harness, session_id, message_id, ordinal, tool_name, tool_input) "
        "VALUES (?, ?, ?, ?, ?, '{}')",
        [harness, session_id, f"{session_id}#0", ordinal, tool_name],
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
        "last_sync": "2026-01-15T03:04:05",
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
    }


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

    unknown = metrics.overview(migrated_con, ["missing"], **window)
    assert list(unknown["per_harness"]) == ["missing"]
    assert unknown["per_harness"]["missing"]["sessions"] == 0
    assert unknown["distinct_projects"] == 0


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
            "days": ["2026-01-10", "2026-01-11", "2026-01-12"],
            "sessions": {"claude": [0, 0, 1], "cursor": [1, 0, 0]},
        },
        "weekly": {
            "weeks": ["2026-01-05", "2026-01-12"],
            "writes": {"claude": [0, 1], "cursor": [1, 0]},
            "reads": {"claude": [0, 0], "cursor": [1, 0]},
        },
    }
