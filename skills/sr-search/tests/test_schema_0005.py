"""Contract tests for migration ``0005_utc_timestamps.sql``.

``0005`` is DML-only: it clears ``_sync_state`` watermarks so the next ingest
re-scans under the UTC-at-rest contract. Product DDL is unchanged vs ``0004``.
The chain is built in a child process that loads ``vss``
(``released_chain_con``); this process reads it without ``vss`` and never
runs an explicit ``CHECKPOINT`` on it.
"""

import json
from datetime import datetime

from stockroom.migrations import discover
from test_schema_0003 import _introspect_schema
from test_schema_0004 import SNAPSHOT_PATH as SNAPSHOT_0004


def test_0005_clears_sync_state_watermarks(released_chain_con) -> None:
    """Applying ``0005`` nulls ``last_mtime`` / ``last_path`` but keeps rows."""
    con = released_chain_con(4)
    con.execute(
        "INSERT INTO _sync_state "
        "(harness, source_root, last_mtime, last_path, updated_at) VALUES "
        "('claude', '/root', TIMESTAMP '2026-01-01 12:00:00', '/root/a.jsonl', "
        "TIMESTAMP '2026-01-01 12:00:00')"
    )
    path = next(m.path for m in discover() if m.version == 5)
    con.execute(path.read_text(encoding="utf-8"))
    row = con.execute(
        "SELECT last_mtime, last_path, updated_at FROM _sync_state "
        "WHERE harness = 'claude' AND source_root = '/root'"
    ).fetchone()
    assert row is not None
    assert row[0] is None
    assert row[1] is None
    assert row[2] == datetime(2026, 1, 1, 12, 0, 0)


def test_0005_schema_matches_0004_snapshot(released_chain_con) -> None:
    """Cumulative DDL after ``0005`` still matches the ``0004`` golden."""
    con = released_chain_con(5)
    actual = _introspect_schema(con)
    expected = json.loads(SNAPSHOT_0004.read_text(encoding="utf-8"))
    assert actual == expected
