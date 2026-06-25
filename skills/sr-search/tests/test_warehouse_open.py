"""The warehouse-open chokepoint: path resolution, the lazy gate, and modes.

``stockroom.warehouse`` is the single contract every consumer goes through to
reach the DuckDB warehouse. These tests pin the harness-neutral home
resolution (``~/.stockroom/``, overridable via ``STOCKROOM_HOME`` for tests),
the auto-created home directory, and — once the gate is wired — that opening a
fresh warehouse returns a ready, migrated connection while opening a current
one never re-runs the runner.
"""

from pathlib import Path

from stockroom import warehouse


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
