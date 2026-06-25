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


def test_apply_pending_applies_0001_on_fresh_db(
    mem_con: duckdb.DuckDBPyConnection,
) -> None:
    """A fresh DB gets ``0001``: five product tables, version 1, recorded row."""
    applied = migrate.apply_pending(mem_con)

    assert applied == [1]
    assert _PRODUCT_TABLES <= _table_names(mem_con)
    assert migrate.current_version(mem_con) == 1

    version, filename, applied_at = mem_con.execute(
        f"SELECT version, filename, applied_at FROM {migrate.SCHEMA_VERSION_TABLE} "
        "WHERE version = 1"
    ).fetchone()
    assert version == 1
    assert filename == "0001_initial_schema.sql"
    assert applied_at is not None


def test_apply_pending_is_idempotent(
    mem_con: duckdb.DuckDBPyConnection,
) -> None:
    """Re-running on a current DB is a no-op: ``[]``, same version, no dup rows."""
    migrate.apply_pending(mem_con)
    second = migrate.apply_pending(mem_con)

    assert second == []
    assert migrate.current_version(mem_con) == 1
    row_count = mem_con.execute(
        f"SELECT count(*) FROM {migrate.SCHEMA_VERSION_TABLE}"
    ).fetchone()[0]
    assert row_count == 1


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
