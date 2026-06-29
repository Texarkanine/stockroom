"""Unit tests for the ``stockroom.query`` library surface.

Covers the pure renderer (``_format_table``) and ``run_query`` against both an
injected connection (the common, fast path) and the owns-connection
open-read-only path. CLI / subprocess behavior lives in ``test_query_cli.py``.
"""

from pathlib import Path

import duckdb

from stockroom import warehouse
from stockroom.query import QueryResult, _format_table, run_query
from stockroom.truncate import ELISION

# --- _format_table ----------------------------------------------------------


def test_format_table_renders_header_and_row() -> None:
    """A single-row result shows the column name, the value, and a ``(1 row)``
    trailer."""
    out = _format_table(["n"], [(1,)])
    assert "n" in out
    assert "1" in out
    assert out.rstrip().endswith("(1 row)")


def test_format_table_empty_keeps_header_and_zero_trailer() -> None:
    """An empty result still names its column and ends with ``(0 rows)``."""
    out = _format_table(["n"], [])
    assert "n" in out
    assert out.rstrip().endswith("(0 rows)")


def test_format_table_row_count_trailer_pluralizes() -> None:
    """The trailer pluralizes: ``(2 rows)`` for a two-row result."""
    out = _format_table(["n"], [(1,), (2,)])
    assert out.rstrip().endswith("(2 rows)")


def test_format_table_renders_none_as_null() -> None:
    """A ``None`` cell renders as the literal ``NULL``."""
    out = _format_table(["c"], [(None,)])
    assert "NULL" in out


def test_format_table_truncates_wide_cell_by_default() -> None:
    """A cell wider than the default (snippet) budget is elided with a marker,
    and the full value does not appear in the rendered table."""
    out = _format_table(["c"], [("x" * 600,)])
    assert ELISION in out
    assert "x" * 600 not in out


def test_format_table_full_detail_keeps_whole_cell() -> None:
    """``detail="full"`` renders the entire cell verbatim — no marker, full value."""
    out = _format_table(["c"], [("x" * 600,)], detail="full")
    assert "x" * 600 in out
    assert ELISION not in out


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

    raised = False
    try:
        run_query("CREATE TABLE scratch (x INTEGER)")
    except duckdb.Error:
        raised = True
    assert raised, "a write through the read-only query surface must raise"
