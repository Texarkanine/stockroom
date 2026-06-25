"""The warehouse-open chokepoint: path resolution, the lazy gate, and modes.

``stockroom.warehouse`` is the single contract every consumer goes through to
reach the DuckDB warehouse. These tests pin the harness-neutral home
resolution (``~/.stockroom/``, overridable via ``STOCKROOM_HOME`` for tests),
the auto-created home directory, and — once the gate is wired — that opening a
fresh warehouse returns a ready, migrated connection while opening a current
one never re-runs the runner.
"""

import json
from pathlib import Path

import duckdb

from stockroom import migrate, warehouse
from test_schema_0001 import SNAPSHOT_PATH, _introspect_schema

_PRODUCT_TABLES = {"sessions", "messages", "tool_calls", "embeddings", "_sync_state"}


def _table_names(con: duckdb.DuckDBPyConnection) -> set[str]:
    return {
        r[0]
        for r in con.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'main'"
        ).fetchall()
    }


# --- path resolution + WarehouseBusyError (step 4) --------------------------


def test_warehouse_busy_error_is_an_exception() -> None:
    """``WarehouseBusyError`` is importable and is an ``Exception`` subclass."""
    assert issubclass(warehouse.WarehouseBusyError, Exception)


def test_paths_resolve_under_stockroom_home(warehouse_home: Path) -> None:
    """``warehouse_path`` / ``lock_path`` live under the ``STOCKROOM_HOME`` dir."""
    assert warehouse.home_dir() == warehouse_home
    assert warehouse.warehouse_path() == warehouse_home / "warehouse.duckdb"
    assert warehouse.lock_path() == warehouse_home / ".warehouse.lock"


def test_home_dir_is_auto_created(warehouse_home: Path) -> None:
    """The home directory is created on first resolution if it is absent."""
    assert not warehouse_home.exists()
    resolved = warehouse.home_dir()
    assert resolved == warehouse_home
    assert resolved.is_dir()


# --- open() lazy gate (step 6) ----------------------------------------------


def test_open_writer_on_fresh_path_returns_migrated_connection(
    warehouse_home: Path,
) -> None:
    """``open(read_only=False)`` on a brand-new path migrates and is ready."""
    con = warehouse.open(read_only=False)
    try:
        assert migrate.current_version(con) == 1
        assert _PRODUCT_TABLES <= _table_names(con)
        # The warehouse file was created at the resolved path.
        assert warehouse.warehouse_path().is_file()
    finally:
        con.close()


def test_open_reader_on_current_warehouse_returns_working_connection(
    warehouse_home: Path,
) -> None:
    """``open(read_only=True)`` on a current warehouse yields a usable RO conn."""
    warehouse.open(read_only=False).close()  # create + migrate first

    con = warehouse.open(read_only=True)
    try:
        assert migrate.current_version(con) == 1
        # A plain read works against the migrated schema.
        assert con.execute("SELECT count(*) FROM sessions").fetchone()[0] == 0
    finally:
        con.close()


def test_open_reader_on_current_warehouse_does_not_invoke_runner(
    warehouse_home: Path, monkeypatch
) -> None:
    """The double-checked gate skips the runner entirely when already current."""
    warehouse.open(read_only=False).close()  # create + migrate first

    def _must_not_run(*args, **kwargs):
        raise AssertionError("apply_pending must not run on a current warehouse")

    monkeypatch.setattr(warehouse, "apply_pending", _must_not_run)

    con = warehouse.open(read_only=True)
    try:
        assert migrate.current_version(con) == 1
    finally:
        con.close()


# --- radical-innovation guard: the framework yields exactly the locked DDL --


def test_migrated_warehouse_matches_locked_snapshot(warehouse_home: Path) -> None:
    """A freshly opened warehouse's product schema byte-matches m1's snapshot.

    Reuses milestone 1's introspection helper. The runner-owned
    ``schema_version`` bookkeeping table is excluded (it is not part of
    ``0001``), proving the migration framework produces precisely the locked
    product DDL — and handing milestone 3 the guarantee that "opening the
    warehouse yields the locked schema."
    """
    con = warehouse.open(read_only=False)
    try:
        schema = _introspect_schema(con)
    finally:
        con.close()

    schema.pop(migrate.SCHEMA_VERSION_TABLE, None)
    expected = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    assert schema == expected
