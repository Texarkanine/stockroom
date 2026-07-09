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
import pytest

from stockroom import migrate, warehouse
from stockroom.migrations import discover
from test_schema_0004 import SNAPSHOT_PATH
from test_schema_0003 import _introspect_schema

_PRODUCT_TABLES = {"sessions", "messages", "tool_calls", "embeddings", "_sync_state"}
_HEAD_VERSION = 4


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
        assert migrate.current_version(con) == _HEAD_VERSION
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
        assert migrate.current_version(con) == _HEAD_VERSION
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
        assert migrate.current_version(con) == _HEAD_VERSION
    finally:
        con.close()


def test_open_reader_has_vss_loaded(warehouse_home: Path) -> None:
    """An opened reader has ``vss`` loaded and its persistence ``SET`` applied.

    Resolves the preflight advisory: ``ensure_vss`` runs ``LOAD vss`` + the
    per-connection ``SET hnsw_enable_experimental_persistence`` on read-only
    connections too (m2 readers need ``vss`` for vector ops), and both are
    session-level — not DB writes — so they succeed against a read-only DuckDB
    handle. The setting only *exists* once ``vss`` is loaded, so reading it as
    ``true`` proves both halves ran on the reader.
    """
    warehouse.open(read_only=False).close()  # create + migrate first

    con = warehouse.open(read_only=True)
    try:
        loaded = con.execute(
            "SELECT loaded FROM duckdb_extensions() WHERE extension_name = 'vss'"
        ).fetchone()[0]
        assert loaded is True
        setting = con.execute(
            "SELECT current_setting('hnsw_enable_experimental_persistence')"
        ).fetchone()[0]
        assert setting is True
    finally:
        con.close()


def test_open_with_migrate_false_skips_the_gate(
    warehouse_home: Path, monkeypatch
) -> None:
    """``migrate=False`` opens the warehouse as-is, bypassing the runner entirely."""
    warehouse.open(read_only=False).close()  # create + migrate first

    def _must_not_run(*args, **kwargs):
        raise AssertionError("the runner must not run when migrate=False")

    monkeypatch.setattr(warehouse, "apply_pending", _must_not_run)

    con = warehouse.open(read_only=True, migrate=False)
    try:
        assert con.execute("SELECT count(*) FROM sessions").fetchone()[0] == 0
    finally:
        con.close()


def test_open_current_returns_read_only_current_connection(
    warehouse_home: Path,
) -> None:
    """A current warehouse opens read-only without invoking a write path."""
    warehouse.open(read_only=False).close()

    con = warehouse.open_current()
    try:
        assert migrate.current_version(con) == _HEAD_VERSION
        with pytest.raises(duckdb.Error):
            con.execute("CREATE TABLE forbidden (id INTEGER)")
    finally:
        con.close()


def test_open_current_refuses_stale_schema_without_migrating(
    warehouse_home: Path,
) -> None:
    """A behind-head warehouse raises typed staleness and stays behind."""
    path = warehouse.warehouse_path()
    con = duckdb.connect(str(path))
    migration = next(item for item in discover() if item.version == 1)
    try:
        con.execute(migration.path.read_text(encoding="utf-8"))
        migrate.ensure_schema_version_table(con)
        con.execute(
            f"INSERT INTO {migrate.SCHEMA_VERSION_TABLE} (version, filename) "
            "VALUES (1, ?)",
            [migration.path.name],
        )
    finally:
        con.close()

    with pytest.raises(warehouse.WarehouseStaleError) as caught:
        warehouse.open_current()
    assert caught.value.current == 1
    assert caught.value.latest == _HEAD_VERSION
    assert "stockroom migrate" in str(caught.value)

    con = duckdb.connect(str(path), read_only=True)
    try:
        assert migrate.current_version(con) == 1
        assert "source_mtime" not in {
            row[0]
            for row in con.execute(
                "SELECT column_name FROM duckdb_columns() "
                "WHERE table_name = 'sessions'"
            ).fetchall()
        }
    finally:
        con.close()


# --- radical-innovation guard: the framework yields exactly the locked DDL --


def test_migrated_warehouse_matches_locked_snapshot(warehouse_home: Path) -> None:
    """A freshly opened warehouse's product schema byte-matches the head snapshot.

    Reuses the schema-introspection helper against the *cumulative* post-``0004``
    golden (``0004_snapshot.json``: columns + PKs + the HNSW index). The
    runner-owned ``schema_version`` bookkeeping table is excluded by the helper
    (it is not part of any product migration), proving the migration framework
    produces precisely the locked product DDL — including the VSS index — at the
    chain head: opening the warehouse yields the current locked schema.
    """
    con = warehouse.open(read_only=False)
    try:
        schema = _introspect_schema(con)
    finally:
        con.close()

    expected = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    assert schema == expected
