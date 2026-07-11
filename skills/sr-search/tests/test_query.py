"""Unit tests for the ``stockroom.query`` library surface.

Covers ``run_query`` against both an injected connection (the common, fast path)
and the owns-connection open-read-only path. The pure rendering now lives in
``stockroom.render`` (tested in ``test_render.py``); CLI / subprocess behavior
lives in ``test_query_cli.py``.
"""

from pathlib import Path

import duckdb
import pytest

from stockroom import warehouse
from stockroom.query import QueryResult, run_query

# --- run_query (injected connection) ----------------------------------------


def test_run_query_returns_columns_and_rows(migrated_con) -> None:
    """``SELECT 1 AS n`` yields column ``n`` and row ``(1,)``."""
    result = run_query("SELECT 1 AS n", con=migrated_con)
    assert isinstance(result, QueryResult)
    assert result.columns == ["n"]
    assert result.rows == [(1,)]


def test_run_query_over_real_schema(migrated_con) -> None:
    """A query over a seeded ``sessions`` row returns it — proving the surface
    works against the actual migrated (0001+0002) schema."""
    migrated_con.execute(
        "INSERT INTO sessions (harness, session_id, project_id, source_path, "
        "is_subagent) VALUES ('cursor', 's1', 'slug-x', '/p/s1.jsonl', false)"
    )
    result = run_query(
        "SELECT harness, project_id FROM sessions ORDER BY session_id",
        con=migrated_con,
    )
    assert result.columns == ["harness", "project_id"]
    assert result.rows == [("cursor", "slug-x")]


def test_run_query_empty_result_keeps_columns(migrated_con) -> None:
    """An empty result set still reports its column names with zero rows."""
    result = run_query("SELECT harness FROM sessions WHERE 1 = 0", con=migrated_con)
    assert result.columns == ["harness"]
    assert result.rows == []


# --- run_query (owns-connection, opens read-only) ---------------------------


def test_run_query_opens_read_only_when_no_con(warehouse_home: Path) -> None:
    """With no injected connection, ``run_query`` opens the warehouse itself
    (read-only) and returns results against it."""
    writer = warehouse.open(read_only=False)
    try:
        writer.execute(
            "INSERT INTO sessions (harness, session_id, project_id, source_path, "
            "is_subagent) VALUES ('claude', 's1', 'slug-y', '/p/s1.jsonl', false)"
        )
    finally:
        writer.close()

    result = run_query("SELECT count(*) AS c FROM sessions")
    assert result.rows == [(1,)]


def test_run_query_no_con_is_read_only(warehouse_home: Path) -> None:
    """The owns-connection path opens read-only: a write statement is rejected
    by DuckDB rather than mutating the warehouse."""
    warehouse.open(read_only=False).close()  # create + migrate

    with pytest.raises(duckdb.Error):
        run_query("CREATE TABLE scratch (x INTEGER)")
