"""Contract tests for migration ``0004_observation_times.sql``.

``0004`` adds two uniform time meanings without fabricating source-authored
timestamps: the source transcript mtime on sessions and stockroom's first
observation time on messages. Earlier migrations and snapshots remain frozen;
this module locks the new cumulative schema head. The chain is built in a
child process that loads ``vss`` (``released_chain_con``); this process reads
it without ``vss``.
"""

import json
import os
from pathlib import Path

import duckdb

from test_schema_0003 import _introspect_schema

SNAPSHOT_PATH = Path(__file__).parent / "fixtures" / "schema" / "0004_snapshot.json"


def _columns(con: duckdb.DuckDBPyConnection, table: str) -> set[str]:
    rows = con.execute(
        "SELECT column_name FROM duckdb_columns() "
        "WHERE schema_name = 'main' AND table_name = ?",
        [table],
    ).fetchall()
    return {row[0] for row in rows}


def test_0004_adds_session_source_mtime(released_chain_con) -> None:
    """Sessions gain the source transcript mtime used as activity provenance."""
    con = released_chain_con(4)
    assert "source_mtime" in _columns(con, "sessions")


def test_0004_adds_message_first_seen_at(released_chain_con) -> None:
    """Messages gain the time at which stockroom first observed them."""
    con = released_chain_con(4)
    assert "first_seen_at" in _columns(con, "messages")


def test_migrated_schema_matches_0004_snapshot(released_chain_con) -> None:
    """The cumulative post-``0004`` schema byte-matches its golden snapshot."""
    con = released_chain_con(4)
    actual = _introspect_schema(con)

    if os.environ.get("STOCKROOM_UPDATE_SCHEMA_GOLDEN"):
        SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
        SNAPSHOT_PATH.write_text(
            json.dumps(actual, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    assert SNAPSHOT_PATH.is_file(), f"golden schema snapshot missing: {SNAPSHOT_PATH}"
    expected = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    assert actual == expected
