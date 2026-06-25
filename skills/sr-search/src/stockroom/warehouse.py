"""The warehouse-open chokepoint: the single contract for reaching the DB.

Every stockroom consumer (skills, the nightly job, ``sr-query``) opens the
DuckDB warehouse through this module — never by connecting directly. That
makes ``warehouse.open()`` the one place where the lazy migration gate runs,
so no consumer can ever touch an un-migrated database (and the session-start
hook simply never calls it, satisfying "the hook never migrates").

This module owns:

* **Path resolution** — the harness-neutral warehouse home (``~/.stockroom/``,
  overridable via the ``STOCKROOM_HOME`` env var for tests), auto-created on
  first use; the warehouse file and the sidecar lock file beside it.
* **The coordination lock** — an ``fcntl.flock`` single-writer/migrator token
  (added in a later build step).
* **Reader/writer backoff** — bounded retry around DuckDB's open-time
  "Could not set lock" ``IOException``, terminating in a typed
  :class:`WarehouseBusyError` (added in a later build step).

Concurrency design rationale lives in
``memory-bank/active/creative/creative-warehouse-concurrency-locking.md``.
"""

import fcntl
import os
import random
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path

import duckdb

#: Env var that overrides the warehouse home (used by tests to redirect away
#: from the operator's real ``~/.stockroom/``). Later milestones (ingest,
#: sr-query, dashboard) adopt the same name.
HOME_ENV_VAR = "STOCKROOM_HOME"

#: Filenames placed inside the warehouse home.
WAREHOUSE_FILENAME = "warehouse.duckdb"
LOCK_FILENAME = ".warehouse.lock"

# Bounded exponential-backoff defaults for opening DuckDB while a migrator may
# hold the warehouse read-write. Injectable per-call for tests.
_INITIAL_DELAY = 0.05  # seconds
_BACKOFF_FACTOR = 2.0
_MAX_DELAY = 1.0  # per-attempt cap
_TOTAL_TIMEOUT = 30.0  # overall budget before WarehouseBusyError


class WarehouseBusyError(RuntimeError):
    """Raised when the warehouse stays locked past the caller's timeout.

    A reader hits this when a migrator holds the warehouse read-write for
    longer than the backoff budget; a writer/migrator hits it when readers
    fail to drain in time. It is the typed, fail-soft-visible terminal state —
    never a raw DuckDB ``IOException``, and never an unbounded block.
    """


def home_dir() -> Path:
    """Return the warehouse home directory, creating it if absent.

    Resolves ``STOCKROOM_HOME`` when set (tests), else ``~/.stockroom``. The
    directory is created (with parents) on first resolution so callers can
    rely on it existing.
    """
    override = os.environ.get(HOME_ENV_VAR)
    base = Path(override) if override else Path.home() / ".stockroom"
    base.mkdir(parents=True, exist_ok=True)
    return base


def warehouse_path() -> Path:
    """Return the absolute path to the single-file DuckDB warehouse."""
    return home_dir() / WAREHOUSE_FILENAME


def lock_path() -> Path:
    """Return the absolute path to the sidecar coordination lock file."""
    return home_dir() / LOCK_FILENAME


@contextmanager
def _flock(path: Path, *, blocking: bool = True) -> Iterator[int]:
    """Hold an exclusive ``fcntl.flock`` on ``path`` for the context body.

    This is the single-writer / migrator coordination token: a process takes
    it before opening DuckDB read-write. The lock is associated with the open
    file description, so it is released when the file descriptor is closed and
    — crucially — auto-released by the OS if the holding process dies, so a
    crashed migrator can never permanently wedge the warehouse.

    With ``blocking=False`` a contended acquire raises ``BlockingIOError``
    (an ``OSError``) immediately instead of waiting.
    """
    fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o644)
    flags = fcntl.LOCK_EX | (fcntl.LOCK_NB if not blocking else 0)
    try:
        fcntl.flock(fd, flags)
        try:
            yield fd
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


def _is_lock_conflict(exc: duckdb.IOException) -> bool:
    """True when a DuckDB ``IOException`` is the migration-time lock conflict.

    DuckDB raises ``IOException`` for several reasons; only the "Could not set
    lock" / "Conflicting lock" case means another process holds the warehouse.
    Other IO errors (disk, permissions) must propagate immediately rather than
    being retried as if transient.
    """
    message = str(exc).lower()
    return "lock" in message


def _open_with_backoff(
    path: Path,
    *,
    read_only: bool,
    initial_delay: float = _INITIAL_DELAY,
    factor: float = _BACKOFF_FACTOR,
    max_delay: float = _MAX_DELAY,
    timeout: float = _TOTAL_TIMEOUT,
    jitter: bool = True,
    sleep: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
) -> duckdb.DuckDBPyConnection:
    """Open a DuckDB connection, retrying around the migration-time lock.

    Attempts ``duckdb.connect`` and, if it raises the lock-conflict
    ``IOException`` (another process holds the warehouse), backs off with
    bounded exponential delay + jitter and retries until ``timeout`` elapses,
    then raises :class:`WarehouseBusyError`. Any other error propagates
    immediately. The clock/sleep are injectable so tests are instant and
    deterministic.
    """
    deadline = monotonic() + timeout
    delay = initial_delay
    while True:
        try:
            return duckdb.connect(str(path), read_only=read_only)
        except duckdb.IOException as exc:
            if not _is_lock_conflict(exc):
                raise
            now = monotonic()
            if now >= deadline:
                raise WarehouseBusyError(
                    f"warehouse at {path} stayed locked for {timeout}s"
                ) from exc
            capped = min(delay, max_delay)
            wait = capped * (0.5 + 0.5 * random.random()) if jitter else capped
            sleep(min(wait, deadline - now))
            delay = min(delay * factor, max_delay)
