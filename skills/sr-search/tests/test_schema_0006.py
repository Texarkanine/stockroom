"""Contract tests for migration ``0006_workspace_key.sql``.

``0006`` adds nullable ``sessions.workspace_key`` — a cross-harness rollup key
derived at ingest from per-harness strategies (see ``ingest.paths.workspace_key_for``).
Structural only; no DML backfill. Pre-existing rows keep ``NULL`` until
``--full`` re-ingest. Cumulative schema head moves to ``0006_snapshot.json``.
"""

import json
import os
from pathlib import Path

import duckdb

from stockroom import warehouse
from stockroom.migrations import discover
from test_schema_0003 import _introspect_schema

SNAPSHOT_PATH = Path(__file__).parent / "fixtures" / "schema" / "0006_snapshot.json"


def _apply_chain(con: duckdb.DuckDBPyConnection) -> None:
    """Load VSS and apply every packaged migration through ``0006``."""
    warehouse.ensure_vss(con)
    for migration in discover():
        if migration.version > 6:
            break
        con.execute(migration.path.read_text(encoding="utf-8"))


def _sessions_columns(con: duckdb.DuckDBPyConnection) -> set[str]:
    rows = con.execute(
        "SELECT column_name FROM duckdb_columns() "
        "WHERE schema_name = 'main' AND table_name = 'sessions'"
    ).fetchall()
    return {row[0] for row in rows}


def test_0006_adds_workspace_key_column(mem_con: duckdb.DuckDBPyConnection) -> None:
    """Sessions gain nullable ``workspace_key`` after ``0006``."""
    _apply_chain(mem_con)
    assert "workspace_key" in _sessions_columns(mem_con)
    row = mem_con.execute(
        "SELECT data_type, is_nullable FROM duckdb_columns() "
        "WHERE schema_name = 'main' AND table_name = 'sessions' "
        "AND column_name = 'workspace_key'"
    ).fetchone()
    assert row is not None
    assert row[0] == "VARCHAR"
    assert bool(row[1]) is True


def test_0006_preserves_rows_with_null_workspace_key(
    mem_con: duckdb.DuckDBPyConnection,
) -> None:
    """Pre-existing sessions survive with ``workspace_key IS NULL`` (no backfill)."""
    warehouse.ensure_vss(mem_con)
    for migration in discover():
        if migration.version > 5:
            break
        mem_con.execute(migration.path.read_text(encoding="utf-8"))
    mem_con.execute(
        "INSERT INTO sessions (harness, session_id, project_id, cwd, "
        "source_path, is_subagent) "
        "VALUES ('cursor', 's1', 'home-x-stockroom', '/home/x/stockroom', "
        "'/p/s1.jsonl', false)"
    )
    path = next(m.path for m in discover() if m.version == 6)
    mem_con.execute(path.read_text(encoding="utf-8"))
    row = mem_con.execute(
        "SELECT session_id, project_id, cwd, workspace_key "
        "FROM sessions WHERE session_id = 's1'"
    ).fetchone()
    assert row == ("s1", "home-x-stockroom", "/home/x/stockroom", None)


def test_migrated_schema_matches_0006_snapshot(
    mem_con: duckdb.DuckDBPyConnection,
) -> None:
    """Cumulative post-``0006`` schema byte-matches its golden snapshot."""
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
