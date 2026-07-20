"""Contract tests for migration ``0007_session_token_usage.sql``.

``0007`` adds four nullable BIGINT token columns on ``sessions`` (session-grain
native totals for future harnesses) and creates VIEW ``session_token_usage`` —
the read-time rollup that exposes message sums, native session totals, COALESCE
effective totals, and ``token_grain``. Structural ADD COLUMN + CREATE VIEW only;
no DML backfill. Pre-existing rows keep session tokens NULL. Cumulative schema
head moves to ``0007_snapshot.json``; the VIEW is locked via ``duckdb_views()``
and seeded-row semantics (``_introspect_schema`` covers tables+indexes only).
"""

import json
import os
from pathlib import Path

import duckdb

from stockroom import warehouse
from stockroom.migrations import discover
from test_schema_0003 import _introspect_schema

SNAPSHOT_PATH = Path(__file__).parent / "fixtures" / "schema" / "0007_snapshot.json"

SESSION_TOKEN_COLUMNS = (
    "input_tokens",
    "output_tokens",
    "cache_creation_tokens",
    "cache_read_tokens",
)


def _apply_chain(con: duckdb.DuckDBPyConnection) -> None:
    """Load VSS and apply every packaged migration through ``0007``."""
    warehouse.ensure_vss(con)
    for migration in discover():
        if migration.version > 7:
            break
        con.execute(migration.path.read_text(encoding="utf-8"))


def _apply_through(con: duckdb.DuckDBPyConnection, version: int) -> None:
    """Load VSS and apply packaged migrations through ``version`` inclusive."""
    warehouse.ensure_vss(con)
    for migration in discover():
        if migration.version > version:
            break
        con.execute(migration.path.read_text(encoding="utf-8"))


def _sessions_columns(con: duckdb.DuckDBPyConnection) -> set[str]:
    rows = con.execute(
        "SELECT column_name FROM duckdb_columns() "
        "WHERE schema_name = 'main' AND table_name = 'sessions'"
    ).fetchall()
    return {row[0] for row in rows}


def _view_names(con: duckdb.DuckDBPyConnection) -> set[str]:
    rows = con.execute(
        "SELECT view_name FROM duckdb_views() WHERE schema_name = 'main'"
    ).fetchall()
    return {row[0] for row in rows}


def _view_columns(con: duckdb.DuckDBPyConnection, view_name: str) -> set[str]:
    rows = con.execute(
        "SELECT column_name FROM duckdb_columns() "
        "WHERE schema_name = 'main' AND table_name = ?",
        [view_name],
    ).fetchall()
    return {row[0] for row in rows}


def test_0007_adds_nullable_session_token_columns(
    mem_con: duckdb.DuckDBPyConnection,
) -> None:
    """Sessions gain four nullable BIGINT token columns after ``0007``."""
    _apply_chain(mem_con)
    cols = _sessions_columns(mem_con)
    for name in SESSION_TOKEN_COLUMNS:
        assert name in cols
        row = mem_con.execute(
            "SELECT data_type, is_nullable FROM duckdb_columns() "
            "WHERE schema_name = 'main' AND table_name = 'sessions' "
            "AND column_name = ?",
            [name],
        ).fetchone()
        assert row is not None
        assert row[0] == "BIGINT"
        assert bool(row[1]) is True


def test_0007_creates_session_token_usage_view(
    mem_con: duckdb.DuckDBPyConnection,
) -> None:
    """VIEW ``session_token_usage`` exists with the dual-grain rollup columns."""
    _apply_chain(mem_con)
    assert "session_token_usage" in _view_names(mem_con)
    cols = _view_columns(mem_con, "session_token_usage")
    expected = {
        "harness",
        "session_id",
        "input_tokens_from_messages",
        "output_tokens_from_messages",
        "cache_creation_tokens_from_messages",
        "cache_read_tokens_from_messages",
        "input_tokens_native",
        "output_tokens_native",
        "cache_creation_tokens_native",
        "cache_read_tokens_native",
        "input_tokens_total",
        "output_tokens_total",
        "cache_creation_tokens_total",
        "cache_read_tokens_total",
        "token_grain",
    }
    assert expected <= cols


def test_0007_preserves_rows_with_null_session_tokens(
    mem_con: duckdb.DuckDBPyConnection,
) -> None:
    """Pre-existing sessions survive with session token columns NULL (no backfill)."""
    _apply_through(mem_con, 6)
    mem_con.execute(
        "INSERT INTO sessions (harness, session_id, project_id, cwd, "
        "source_path, is_subagent) "
        "VALUES ('cursor', 's1', 'home-x-stockroom', '/home/x/stockroom', "
        "'/p/s1.jsonl', false)"
    )
    path = next(m.path for m in discover() if m.version == 7)
    mem_con.execute(path.read_text(encoding="utf-8"))
    row = mem_con.execute(
        "SELECT session_id, input_tokens, output_tokens, "
        "cache_creation_tokens, cache_read_tokens "
        "FROM sessions WHERE session_id = 's1'"
    ).fetchone()
    assert row == ("s1", None, None, None, None)


def test_session_token_usage_message_grain_rollup(
    mem_con: duckdb.DuckDBPyConnection,
) -> None:
    """Message-only tokens: from_messages = SUM, totals = sums, grain ``message``."""
    _apply_chain(mem_con)
    mem_con.execute(
        "INSERT INTO sessions (harness, session_id, source_path, is_subagent) "
        "VALUES ('claude', 'msg-only', '/p/m.jsonl', false)"
    )
    mem_con.execute(
        "INSERT INTO messages (harness, session_id, message_id, ordinal, role, "
        "input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens) "
        "VALUES "
        "('claude', 'msg-only', 'msg-only#0', 0, 'user', NULL, NULL, NULL, NULL), "
        "('claude', 'msg-only', 'msg-only#1', 1, 'assistant', 10, 5, 1, 100), "
        "('claude', 'msg-only', 'msg-only#2', 2, 'assistant', 20, 7, NULL, 50)"
    )
    row = mem_con.execute(
        "SELECT input_tokens_from_messages, output_tokens_from_messages, "
        "cache_creation_tokens_from_messages, cache_read_tokens_from_messages, "
        "input_tokens_native, output_tokens_native, "
        "input_tokens_total, output_tokens_total, "
        "cache_creation_tokens_total, cache_read_tokens_total, token_grain "
        "FROM session_token_usage "
        "WHERE harness = 'claude' AND session_id = 'msg-only'"
    ).fetchone()
    assert row == (30, 12, 1, 150, None, None, 30, 12, 1, 150, "message")


def test_session_token_usage_session_grain_native(
    mem_con: duckdb.DuckDBPyConnection,
) -> None:
    """Native-only tokens: totals = native, from_messages NULL, grain ``session``."""
    _apply_chain(mem_con)
    mem_con.execute(
        "INSERT INTO sessions (harness, session_id, source_path, is_subagent, "
        "input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens) "
        "VALUES ('future', 'native-only', '/p/n.jsonl', false, 1000, 200, 10, 50)"
    )
    row = mem_con.execute(
        "SELECT input_tokens_from_messages, output_tokens_from_messages, "
        "input_tokens_native, output_tokens_native, "
        "cache_creation_tokens_native, cache_read_tokens_native, "
        "input_tokens_total, output_tokens_total, "
        "cache_creation_tokens_total, cache_read_tokens_total, token_grain "
        "FROM session_token_usage "
        "WHERE harness = 'future' AND session_id = 'native-only'"
    ).fetchone()
    assert row == (None, None, 1000, 200, 10, 50, 1000, 200, 10, 50, "session")


def test_session_token_usage_both_grains_prefer_native(
    mem_con: duckdb.DuckDBPyConnection,
) -> None:
    """When both grains are present, totals COALESCE to native; both series visible."""
    _apply_chain(mem_con)
    mem_con.execute(
        "INSERT INTO sessions (harness, session_id, source_path, is_subagent, "
        "input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens) "
        "VALUES ('synth', 'both', '/p/b.jsonl', false, 999, 88, 7, 6)"
    )
    mem_con.execute(
        "INSERT INTO messages (harness, session_id, message_id, ordinal, role, "
        "input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens) "
        "VALUES ('synth', 'both', 'both#0', 0, 'assistant', 10, 5, 1, 2)"
    )
    row = mem_con.execute(
        "SELECT input_tokens_from_messages, input_tokens_native, "
        "input_tokens_total, output_tokens_from_messages, output_tokens_native, "
        "output_tokens_total, token_grain "
        "FROM session_token_usage "
        "WHERE harness = 'synth' AND session_id = 'both'"
    ).fetchone()
    assert row == (10, 999, 999, 5, 88, 88, "session")


def test_session_token_usage_none_grain_empty_session(
    mem_con: duckdb.DuckDBPyConnection,
) -> None:
    """Session with no messages and NULL native tokens: grain ``none``, totals NULL."""
    _apply_chain(mem_con)
    mem_con.execute(
        "INSERT INTO sessions (harness, session_id, source_path, is_subagent) "
        "VALUES ('cursor', 'empty', '/p/e.jsonl', false)"
    )
    row = mem_con.execute(
        "SELECT input_tokens_from_messages, input_tokens_native, "
        "input_tokens_total, token_grain "
        "FROM session_token_usage "
        "WHERE harness = 'cursor' AND session_id = 'empty'"
    ).fetchone()
    assert row == (None, None, None, "none")


def test_migrated_schema_matches_0007_snapshot(
    mem_con: duckdb.DuckDBPyConnection,
) -> None:
    """Cumulative post-``0007`` schema byte-matches its golden snapshot."""
    _apply_chain(mem_con)
    actual = _introspect_schema(mem_con)

    if os.environ.get("STOCKROOM_UPDATE_SCHEMA_GOLDEN"):
        SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
        SNAPSHOT_PATH.write_text(
            json.dumps(actual, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    assert SNAPSHOT_PATH.is_file(), f"golden schema snapshot missing: {SNAPSHOT_PATH}"
    expected = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    assert actual == expected
