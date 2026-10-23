"""Contract tests for migration ``0008_entrypoint.sql``.

``0008`` adds nullable ``sessions.entrypoint`` — surface provenance for how a
session was entered (Claude native passthrough; Cursor synthesized ``cli`` /
``ide``). Structural only; no DML backfill. Pre-existing rows keep ``NULL``
until ``--full`` re-ingest. Cumulative schema head moves to
``0008_snapshot.json``.
The chain is built in a child process that loads ``vss``
(``released_chain_con``); this process reads it without ``vss`` and never
runs an explicit ``CHECKPOINT`` on it.
"""

import json
import os
from pathlib import Path

import duckdb

from stockroom.migrations import discover
from test_schema_0003 import _introspect_schema

SNAPSHOT_PATH = Path(__file__).parent / "fixtures" / "schema" / "0008_snapshot.json"


def _sessions_columns(con: duckdb.DuckDBPyConnection) -> set[str]:
    rows = con.execute(
        "SELECT column_name FROM duckdb_columns() "
        "WHERE schema_name = 'main' AND table_name = 'sessions'"
    ).fetchall()
    return {row[0] for row in rows}


def test_0008_adds_entrypoint_column(released_chain_con) -> None:
    """Sessions gain nullable ``entrypoint`` after ``0008``."""
    con = released_chain_con(8)
    assert "entrypoint" in _sessions_columns(con)
    row = con.execute(
        "SELECT data_type, is_nullable FROM duckdb_columns() "
        "WHERE schema_name = 'main' AND table_name = 'sessions' "
        "AND column_name = 'entrypoint'"
    ).fetchone()
    assert row is not None
    assert row[0] == "VARCHAR"
    assert bool(row[1]) is True


def test_0008_preserves_rows_with_null_entrypoint(released_chain_con) -> None:
    """Pre-existing sessions survive with ``entrypoint IS NULL`` (no backfill)."""
    con = released_chain_con(7)
    con.execute(
        "INSERT INTO sessions (harness, session_id, project_id, cwd, "
        "source_path, is_subagent) "
        "VALUES ('cursor', 's1', 'home-x-stockroom', '/home/x/stockroom', "
        "'/p/s1.jsonl', false)"
    )
    path = next(m.path for m in discover() if m.version == 8)
    con.execute(path.read_text(encoding="utf-8"))
    row = con.execute(
        "SELECT session_id, project_id, cwd, entrypoint "
        "FROM sessions WHERE session_id = 's1'"
    ).fetchone()
    assert row == ("s1", "home-x-stockroom", "/home/x/stockroom", None)


def test_migrated_schema_matches_0008_snapshot(released_chain_con) -> None:
    """Cumulative post-``0008`` schema byte-matches its golden snapshot."""
    con = released_chain_con(8)
    actual = _introspect_schema(con)

    if os.environ.get("STOCKROOM_UPDATE_SCHEMA_GOLDEN"):
        SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
        SNAPSHOT_PATH.write_text(
            json.dumps(actual, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    assert SNAPSHOT_PATH.is_file(), f"golden schema snapshot missing: {SNAPSHOT_PATH}"
    expected = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    assert actual == expected
