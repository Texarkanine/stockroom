"""Multi-process concurrency contract for the warehouse chokepoint.

These are the "never break your warehouse" tests: real subprocesses exercise
DuckDB's *cross-process* file lock (read-write exclusive, read-only shared)
together with the framework's flock + bounded backoff. Assertions are on
outcomes (final version, error type, no double-apply, DB intact), never on
exact timings — timeouts and holds are generous and the parent synchronizes on
sentinel files rather than guessing with ``sleep``.
"""

import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

from stockroom import migrate, warehouse
from stockroom.warehouse import WarehouseBusyError

_PRODUCT_TABLES = {"sessions", "messages", "tool_calls", "embeddings", "_sync_state"}


def _create_current_warehouse() -> None:
    """Create + migrate the warehouse via a writer, releasing all locks."""
    warehouse.open(read_only=False).close()


def test_reader_times_out_with_warehouse_busy_during_migration(
    warehouse_home: Path,
    spawn_worker: Callable[..., subprocess.Popen],
    wait_for_sentinel: Callable[[Path], None],
    tmp_path: Path,
) -> None:
    """While a migrator holds RW, a short-timeout reader raises WarehouseBusyError."""
    _create_current_warehouse()
    ready = tmp_path / "rw_ready"
    spawn_worker("hold_rw", ready, 3.0)
    wait_for_sentinel(ready)

    with pytest.raises(WarehouseBusyError):
        warehouse.open(read_only=True, timeout=0.5, initial_delay=0.02)


def test_reader_succeeds_after_migration_releases(
    warehouse_home: Path,
    spawn_worker: Callable[..., subprocess.Popen],
    wait_for_sentinel: Callable[[Path], None],
    tmp_path: Path,
) -> None:
    """A patient reader backs off through the RW hold and then opens cleanly."""
    _create_current_warehouse()
    ready = tmp_path / "rw_ready"
    spawn_worker("hold_rw", ready, 1.0)
    wait_for_sentinel(ready)

    con = warehouse.open(read_only=True, timeout=15.0, initial_delay=0.02)
    try:
        assert migrate.current_version(con) == 2
    finally:
        con.close()


def test_writer_times_out_with_typed_error_while_readers_held(
    warehouse_home: Path,
    spawn_worker: Callable[..., subprocess.Popen],
    wait_for_sentinel: Callable[[Path], None],
    tmp_path: Path,
) -> None:
    """A writer that cannot drain readers in time raises the typed busy error.

    Doubles as the "typed terminal error" guarantee: the timeout surfaces as
    ``WarehouseBusyError``, never a raw DuckDB ``IOException``.
    """
    _create_current_warehouse()
    ready = tmp_path / "ro_ready"
    spawn_worker("hold_ro", ready, 3.0)
    wait_for_sentinel(ready)

    with pytest.raises(WarehouseBusyError):
        warehouse.open(read_only=False, timeout=0.5, initial_delay=0.02)


def test_racing_migrators_serialize_without_double_apply(
    warehouse_home: Path,
    spawn_worker: Callable[..., subprocess.Popen],
    tmp_path: Path,
) -> None:
    """Two processes racing to migrate a fresh warehouse both land at head, once.

    The flock serializes the would-be migrators and the double-checked gate
    stops the loser from re-applying: both observe the head version, exactly one
    bookkeeping row exists *per applied migration* (no double-apply), and the
    product schema is intact.
    """
    out_a = tmp_path / "a.txt"
    out_b = tmp_path / "b.txt"
    proc_a = spawn_worker("migrate_report", out_a)
    proc_b = spawn_worker("migrate_report", out_b)
    assert proc_a.wait(timeout=30) == 0
    assert proc_b.wait(timeout=30) == 0

    assert out_a.read_text(encoding="utf-8") == "2"
    assert out_b.read_text(encoding="utf-8") == "2"

    con = warehouse.open(read_only=True)
    try:
        row_count = con.execute(
            f"SELECT count(*) FROM {migrate.SCHEMA_VERSION_TABLE}"
        ).fetchone()[0]
        assert row_count == 2
        tables = {
            r[0]
            for r in con.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'main'"
            ).fetchall()
        }
        assert _PRODUCT_TABLES <= tables
    finally:
        con.close()
