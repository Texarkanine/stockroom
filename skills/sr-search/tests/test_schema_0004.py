"""Contract tests for migration ``0004_observation_times.sql``.

``0004`` adds two uniform time meanings without fabricating source-authored
timestamps: the source transcript mtime on sessions and stockroom's first
observation time on messages. Earlier migrations and snapshots remain frozen;
this module locks the new cumulative schema head.
"""

import json
import os
from pathlib import Path

import duckdb

from stockroom import warehouse
from stockroom.migrations import discover
from test_schema_0003 import _introspect_schema

SNAPSHOT_PATH = Path(__file__).parent / "fixtures" / "schema" / "0004_snapshot.json"


def _apply_chain(con: duckdb.DuckDBPyConnection) -> None:
    """Load VSS and apply every packaged migration through ``0004``."""
    warehouse.ensure_vss(con)
    for migration in discover():
        if migration.version > 4:
            break
        con.execute(migration.path.read_text(encoding="utf-8"))


def _columns(con: duckdb.DuckDBPyConnection, table: str) -> set[str]:
    rows = con.execute(
        "SELECT column_name FROM duckdb_columns() "
        "WHERE schema_name = 'main' AND table_name = ?",
        [table],
    ).fetchall()
    return {row[0] for row in rows}


def test_0004_adds_session_source_mtime(mem_con: duckdb.DuckDBPyConnection) -> None:
    """Sessions gain the source transcript mtime used as activity provenance."""
    _apply_chain(mem_con)
    assert "source_mtime" in _columns(mem_con, "sessions")


def test_0004_adds_message_first_seen_at(
    mem_con: duckdb.DuckDBPyConnection,
) -> None:
    """Messages gain the time at which stockroom first observed them."""
    _apply_chain(mem_con)
    assert "first_seen_at" in _columns(mem_con, "messages")


def test_migrated_schema_matches_0004_snapshot(
    mem_con: duckdb.DuckDBPyConnection,
) -> None:
    """The cumulative post-``0004`` schema byte-matches its golden snapshot."""
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
