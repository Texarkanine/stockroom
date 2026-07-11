"""Contract tests for migration ``0005_utc_timestamps.sql``.

``0005`` is DML-only: it clears ``_sync_state`` watermarks so the next ingest
re-scans under the UTC-at-rest contract. Product DDL is unchanged vs ``0004``.
"""

import json
from datetime import datetime

import duckdb

from stockroom import warehouse
from stockroom.migrations import discover
from test_schema_0003 import _introspect_schema
from test_schema_0004 import SNAPSHOT_PATH as SNAPSHOT_0004


def _apply_through(con: duckdb.DuckDBPyConnection, *, through_version: int) -> None:
    """Load VSS and apply packaged migrations through ``through_version``."""
    warehouse.ensure_vss(con)
    for migration in discover():
        if migration.version > through_version:
            break
        con.execute(migration.path.read_text(encoding="utf-8"))


def test_0005_clears_sync_state_watermarks(
    mem_con: duckdb.DuckDBPyConnection,
) -> None:
    """Applying ``0005`` nulls ``last_mtime`` / ``last_path`` but keeps rows."""
    _apply_through(mem_con, through_version=4)
    mem_con.execute(
        "INSERT INTO _sync_state "
        "(harness, source_root, last_mtime, last_path, updated_at) VALUES "
        "('claude', '/root', TIMESTAMP '2026-01-01 12:00:00', '/root/a.jsonl', "
        "TIMESTAMP '2026-01-01 12:00:00')"
    )
    path = next(m.path for m in discover() if m.version == 5)
    mem_con.execute(path.read_text(encoding="utf-8"))
    row = mem_con.execute(
        "SELECT last_mtime, last_path, updated_at FROM _sync_state "
        "WHERE harness = 'claude' AND source_root = '/root'"
    ).fetchone()
    assert row is not None
    assert row[0] is None
    assert row[1] is None
    assert row[2] == datetime(2026, 1, 1, 12, 0, 0)


def test_0005_schema_matches_0004_snapshot(
    mem_con: duckdb.DuckDBPyConnection,
) -> None:
    """Cumulative DDL after ``0005`` still matches the ``0004`` golden."""
    _apply_through(mem_con, through_version=5)
    actual = _introspect_schema(mem_con)
    expected = json.loads(SNAPSHOT_0004.read_text(encoding="utf-8"))
    assert actual == expected
