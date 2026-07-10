"""The two low-level primitives behind the warehouse chokepoint.

* ``_flock`` — the ``fcntl.flock`` coordination lock (the single-writer /
  migrator token). Exclusive while held, released on context exit. Tested with
  two open file descriptions in-process: ``flock`` conflicts per open-file
  description, so a second non-blocking acquire fails while the first is held.
* ``_open_with_backoff`` — bounded exponential backoff around DuckDB's
  open-time "Could not set lock" ``IOException``, terminating in a typed
  ``WarehouseBusyError``. The backoff *logic* is unit-tested here by faking
  ``duckdb.connect`` (real cross-process locking is exercised in the
  concurrency suite); a fake clock keeps it instant and deterministic.
"""

import duckdb
import pytest

from stockroom import warehouse
from stockroom.warehouse import WarehouseBusyError


class _FakeClock:
    """A deterministic, instant stand-in for ``time.monotonic`` + ``time.sleep``."""

    def __init__(self) -> None:
        self.t = 0.0

    def monotonic(self) -> float:
        return self.t

    def sleep(self, seconds: float) -> None:
        self.t += seconds


# --- _flock exclusivity + release -------------------------------------------


def test_flock_is_exclusive_while_held_and_releases_on_exit(tmp_path) -> None:
    """A held ``_flock`` blocks a second non-blocking acquire; exit releases it."""
    lock_file = tmp_path / ".warehouse.lock"

    with warehouse._flock(lock_file, blocking=False):
        # A second, independent non-blocking acquire must fail while held.
        with pytest.raises(OSError):
            with warehouse._flock(lock_file, blocking=False):
                pass

    # After the first context exits, the lock is free again.
    with warehouse._flock(lock_file, blocking=False):
        pass


# --- _open_with_backoff -----------------------------------------------------


def test_open_with_backoff_returns_connection_when_unlocked(tmp_path) -> None:
    """When the open succeeds, the live connection is returned as-is."""
    db = tmp_path / "warehouse.duckdb"
    con = warehouse._open_with_backoff(db, read_only=False)
    try:
        assert con.execute("SELECT 42").fetchone()[0] == 42
    finally:
        con.close()


def test_open_with_backoff_raises_warehouse_busy_on_persistent_lock(
    tmp_path, monkeypatch
) -> None:
    """A path that stays lock-conflicted past the timeout raises WarehouseBusyError."""
    calls = {"n": 0}

    def _always_locked(*args, **kwargs):
        calls["n"] += 1
        raise duckdb.IOException("Could not set lock on file: Conflicting lock is held")

    monkeypatch.setattr(duckdb, "connect", _always_locked)
    clock = _FakeClock()

    with pytest.raises(WarehouseBusyError):
        warehouse._open_with_backoff(
            tmp_path / "warehouse.duckdb",
            read_only=True,
            timeout=1.0,
            initial_delay=0.05,
            jitter=False,
            sleep=clock.sleep,
            monotonic=clock.monotonic,
        )

    # It retried rather than giving up on the first conflict.
    assert calls["n"] >= 2


def test_open_with_backoff_reraises_non_lock_ioexception(tmp_path, monkeypatch) -> None:
    """An IOException that is not a lock conflict is re-raised, not retried."""

    def _other_io_error(*args, **kwargs):
        raise duckdb.IOException("disk is on fire")

    monkeypatch.setattr(duckdb, "connect", _other_io_error)

    with pytest.raises(duckdb.IOException, match="disk is on fire"):
        warehouse._open_with_backoff(
            tmp_path / "warehouse.duckdb",
            read_only=True,
            timeout=1.0,
        )
