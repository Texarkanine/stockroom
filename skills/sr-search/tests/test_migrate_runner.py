"""The migration runner: schema_version bookkeeping + forward-only apply.

These tests pin the runner contract decided in the concurrency creative phase:
a runner-owned ``schema_version`` bootstrap table (created via
``CREATE TABLE IF NOT EXISTS``, *not* part of ``0001``), a ``current_version``
read that answers ``0`` before anything is applied, and a forward-only
``apply_pending`` that applies each pending ``NNNN_*.sql`` in ascending order,
each in its own transaction together with its bookkeeping row — atomic,
idempotent, and a no-op when the DB is already current or ahead.

The runner assumes it holds a read-write connection (the caller takes the
flock); concurrency coordination is tested separately.
"""

from collections.abc import Callable
from pathlib import Path

import duckdb
import pytest

from stockroom import migrate
from stockroom.migrations import discover

# Product tables declared by the real ``0001`` migration.
_PRODUCT_TABLES = {"sessions", "messages", "tool_calls", "embeddings", "_sync_state"}


def _table_names(con: duckdb.DuckDBPyConnection) -> set[str]:
    return {
        r[0]
        for r in con.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'main'"
        ).fetchall()
    }


# --- schema_version bootstrap + current_version (step 2) --------------------


def test_current_version_is_zero_when_bookkeeping_table_absent(
    mem_con: duckdb.DuckDBPyConnection,
) -> None:
    """A brand-new DB (no ``schema_version`` table) reads as version 0."""
    assert migrate.current_version(mem_con) == 0


def test_ensure_schema_version_table_is_idempotent(
    mem_con: duckdb.DuckDBPyConnection,
) -> None:
    """``ensure_schema_version_table`` creates the table and is safe to re-run."""
    migrate.ensure_schema_version_table(mem_con)
    migrate.ensure_schema_version_table(mem_con)  # second call must not raise

    names = {
        r[0]
        for r in mem_con.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'main'"
        ).fetchall()
    }
    assert migrate.SCHEMA_VERSION_TABLE in names
    # Created-but-empty still reads as version 0.
    assert migrate.current_version(mem_con) == 0


# --- apply_pending: forward-only application (step 3) -----------------------


def test_apply_pending_applies_all_packaged_on_fresh_db(released_chain_con) -> None:
    """A fresh DB gets every packaged migration in order, landing at the head.

    The product tables come from ``0001``; ``0002`` (workspace identity),
    ``0003`` (the VSS/HNSW embeddings index), ``0004`` (durable observation
    times), ``0005`` (UTC watermark reset), ``0006`` (workspace_key),
    ``0007`` (session tokens + rollup VIEW), ``0008`` (entrypoint), and
    ``0009`` (drops the vector index) are structural follow-ons. A fresh apply
    stamps one bookkeeping row per migration, including ``0001``'s, under its
    packaged filename. ``0003`` needs ``vss`` loaded, which stockroom no longer
    does, so a child process that loads it runs the real runner on a fresh
    file (``released_chain_con``); this process reads the result.
    """
    con = released_chain_con(9)

    rows = con.execute(
        f"SELECT version, filename, applied_at FROM {migrate.SCHEMA_VERSION_TABLE} "
        "ORDER BY version"
    ).fetchall()
    assert [(version, filename) for version, filename, _ in rows] == [
        (m.version, m.path.name) for m in discover()
    ]
    assert [version for version, _, _ in rows] == [1, 2, 3, 4, 5, 6, 7, 8, 9]
    assert rows[0][1] == "0001_initial_schema.sql"
    assert all(applied_at is not None for _, _, applied_at in rows)
    assert _PRODUCT_TABLES <= _table_names(con)
    assert migrate.current_version(con) == 9


def test_apply_pending_is_idempotent(released_chain_con) -> None:
    """Re-running on a current DB is a no-op: ``[]``, same version, no dup rows.

    The chain at the head comes from a child (see above); the second apply
    runs here, without ``vss``, and finds nothing pending.
    """
    con = released_chain_con(9)

    second = migrate.apply_pending(con)

    assert second == []
    assert migrate.current_version(con) == 9
    row_count = con.execute(
        f"SELECT count(*) FROM {migrate.SCHEMA_VERSION_TABLE}"
    ).fetchone()[0]
    assert row_count == len(discover())


def test_apply_pending_applies_in_ascending_order(
    mem_con: duckdb.DuckDBPyConnection,
    tmp_migrations_dir: Callable[..., Path],
) -> None:
    """Pending migrations apply low-to-high; version ends at the highest."""
    directory = tmp_migrations_dir(
        {
            1: "CREATE TABLE alpha (id INTEGER);",
            2: "CREATE TABLE beta (id INTEGER);",
        }
    )
    applied = migrate.apply_pending(mem_con, directory)

    assert applied == [1, 2]
    assert {"alpha", "beta"} <= _table_names(mem_con)
    assert migrate.current_version(mem_con) == 2


def test_apply_pending_rolls_back_a_failing_migration(
    mem_con: duckdb.DuckDBPyConnection,
    tmp_migrations_dir: Callable[..., Path],
) -> None:
    """A migration that fails mid-apply rolls back atomically: no half-state.

    ``0002`` creates a table and then references a non-existent one. The error
    must roll back the whole migration — the just-created table is gone and the
    recorded version stays at 1 (applied-and-recorded, or neither).
    """
    directory = tmp_migrations_dir(
        {
            1: "CREATE TABLE good (id INTEGER);",
            2: (
                "CREATE TABLE half (id INTEGER); "
                "INSERT INTO half SELECT id FROM does_not_exist_xyz;"
            ),
        }
    )
    with pytest.raises(duckdb.Error):
        migrate.apply_pending(mem_con, directory)

    assert migrate.current_version(mem_con) == 1
    assert "good" in _table_names(mem_con)
    assert "half" not in _table_names(mem_con)
    recorded = mem_con.execute(
        f"SELECT count(*) FROM {migrate.SCHEMA_VERSION_TABLE} WHERE version = 2"
    ).fetchone()[0]
    assert recorded == 0


def test_apply_pending_no_op_when_db_is_ahead(
    mem_con: duckdb.DuckDBPyConnection,
    tmp_migrations_dir: Callable[..., Path],
) -> None:
    """When the DB version exceeds the highest known migration, do nothing.

    Forward-compatible read stance: a newer warehouse opened by older code is
    left untouched (no error, no downgrade).
    """
    migrate.ensure_schema_version_table(mem_con)
    mem_con.execute(
        f"INSERT INTO {migrate.SCHEMA_VERSION_TABLE} (version, filename) "
        "VALUES (5, '0005_future.sql')"
    )
    directory = tmp_migrations_dir({1: "CREATE TABLE alpha (id INTEGER);"})

    applied = migrate.apply_pending(mem_con, directory)

    assert applied == []
    assert migrate.current_version(mem_con) == 5
    assert "alpha" not in _table_names(mem_con)
