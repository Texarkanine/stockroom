"""The warehouse-open chokepoint: the single contract for reaching the DB.

Every stockroom consumer (skills, the nightly job, ``sr-query``) opens the
DuckDB warehouse through this module — never by connecting directly.
``warehouse.open()`` owns the lazy migration gate. Hook-launched read surfaces
that are constitutionally forbidden to migrate use ``open_current()`` instead:
it opens read-only and either returns a current schema or refuses with typed
staleness.

This module owns:

* **Warehouse file paths** — ``warehouse.duckdb`` and the sidecar lock beside
  the harness-neutral home (home resolution itself lives in
  :mod:`stockroom.home` and is re-exported here for callers).
* **The coordination lock** — an ``fcntl.flock`` single-writer/migrator token.
* **Reader/writer backoff** — bounded retry around DuckDB's open-time
  "Could not set lock" ``IOException``, terminating in a typed
  :class:`WarehouseBusyError`.

Concurrency design rationale lives in
``memory-bank/active/creative/creative-warehouse-concurrency-locking.md``.
"""

import fcntl
import os
import random
import time
import weakref
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path

import duckdb

from stockroom.home import (
    HOME_ENV_VAR,
    HOME_SOURCE_DEFAULT,
    HOME_SOURCE_OVERRIDE,
    HOME_SOURCE_XDG,
    XDG_DATA_HOME_ENV_VAR,
    home_dir,
    resolve_home,
)
from stockroom.migrate import apply_pending, current_version
from stockroom.migrations import discover

#: Filenames placed inside the warehouse home.
WAREHOUSE_FILENAME = "warehouse.duckdb"
LOCK_FILENAME = ".warehouse.lock"

# Re-export home resolution for existing ``from stockroom.warehouse import …``
# callers. Canonical owner is :mod:`stockroom.home` (DuckDB-free).
__all__ = [
    "HOME_ENV_VAR",
    "HOME_SOURCE_DEFAULT",
    "HOME_SOURCE_OVERRIDE",
    "HOME_SOURCE_XDG",
    "LOCK_FILENAME",
    "WAREHOUSE_FILENAME",
    "XDG_DATA_HOME_ENV_VAR",
    "WarehouseBusyError",
    "WarehouseStaleError",
    "ensure_vss",
    "home_dir",
    "lock_path",
    "open",
    "open_current",
    "resolve_home",
    "warehouse_path",
]

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


class WarehouseStaleError(RuntimeError):
    """Raised when a non-migrating consumer finds the schema behind head.

    ``current`` and ``latest`` make the refusal inspectable while the message
    follows the errmsg ratchet by naming the exact recovery command.
    """

    def __init__(self, current: int, latest: int) -> None:
        self.current = current
        self.latest = latest
        super().__init__(
            f"warehouse schema is behind ({current} < {latest}); "
            "run `stockroom migrate`"
        )


def open_current(
    read_only: bool = True,
    **backoff,
) -> duckdb.DuckDBPyConnection:
    """Open the current warehouse read-only, refusing rather than migrating.

    This is the structural counterpart to :func:`open` for hook-launched
    consumers: it never calls the migration runner. A missing warehouse raises
    ``FileNotFoundError`` with the ingest recovery action; a behind-head
    warehouse closes its connection and raises :class:`WarehouseStaleError`.
    Backoff options are forwarded to the same bounded open helper as
    :func:`open`.
    """
    if not read_only:
        raise ValueError("open_current only supports read_only=True")

    path = warehouse_path()
    if not path.is_file():
        raise FileNotFoundError(
            f"no warehouse found at {path}; run `stockroom ingest` first"
        )

    con = _open_with_backoff(path, read_only=True, **backoff)
    try:
        ensure_vss(con)
        current = current_version(con)
        latest = _latest_version()
        if current < latest:
            raise WarehouseStaleError(current, latest)
        return con
    except BaseException:
        con.close()
        raise


def ensure_vss(con: duckdb.DuckDBPyConnection) -> None:
    """Load the DuckDB ``vss`` extension and enable live HNSW persistence.

    The single place the (rare, provisioning-time) network ``INSTALL`` may
    occur: ``LOAD vss`` is tried first (offline-safe once the extension is
    cached); only if that fails is ``INSTALL vss`` run and the load retried.
    Then ``hnsw_enable_experimental_persistence`` is set so HNSW indexes can be
    created and *modified* (insert/delete) against a persistent DB — a
    per-connection ``SET`` (it is not stored in the DB), so the chokepoint must
    run it on every connection that touches the warehouse post-``0003``.

    Idempotent, and safe on both read-write and read-only connections (``LOAD``
    and ``SET`` are session-level, not DB writes). Keeping the network
    ``INSTALL`` out of the shipped migration SQL preserves the offline /
    supply-chain posture (see
    ``creative-vss-provisioning-and-index.md``).
    """
    try:
        con.execute("LOAD vss")
    except duckdb.Error:
        con.execute("INSTALL vss")
        con.execute("LOAD vss")
    con.execute("SET hnsw_enable_experimental_persistence = true")


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


def _latest_version() -> int:
    """Return the highest discovered migration version (``0`` if none exist)."""
    migrations = discover()
    return migrations[-1].version if migrations else 0


def _release_flock(fd: int) -> None:
    """Release and close a held flock file descriptor (idempotent-ish)."""
    try:
        fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


def _migrate_under_lock(path: Path, target_version: int, **backoff) -> None:
    """Apply pending migrations under the exclusive flock, double-checked.

    Takes the coordination flock (blocking — the single-writer/migrator token),
    re-reads the version inside the lock (another process may have just
    migrated), and only applies pending migrations if still behind. The lock
    and the temporary read-write connection are both released before returning,
    so the subsequent reader open is lock-free.
    """
    with _flock(lock_path()):
        con = _open_with_backoff(path, read_only=False, **backoff)
        try:
            ensure_vss(con)
            if current_version(con) < target_version:
                apply_pending(con)
        finally:
            con.close()


def open(  # noqa: A001 — the warehouse "open" verb is the intended public name
    read_only: bool = False,
    *,
    migrate: bool = True,
    **backoff,
) -> duckdb.DuckDBPyConnection:
    """Open the warehouse through the single chokepoint, migrating if needed.

    This is the one entry every consumer uses; the lazy migration gate lives
    here so no caller can reach an un-migrated database.

    Readers (``read_only=True``) open a connection directly and, via the
    double-checked gate, return immediately when the warehouse is already
    current (the common, near-free path) — taking no flock at all. If the
    warehouse is behind, the reader becomes the migrator (takes the flock,
    re-checks, applies pending migrations, releases) and then reopens read-only.

    Writers (``read_only=False``) take the exclusive flock — the single-writer
    token — for the connection's lifetime (released when the returned
    connection is finalized), open read-write under backoff (waiting for any
    readers to drain), and migrate if behind.

    Set ``migrate=False`` to skip the gate (open as-is). Extra keyword
    arguments are forwarded as backoff parameters to the open helper.
    """
    path = warehouse_path()
    target_version = _latest_version()

    if read_only:
        con = _open_with_backoff(path, read_only=True, **backoff)
        if not migrate or current_version(con) >= target_version:
            ensure_vss(con)
            return con
        # Behind: become the migrator, then reopen read-only for the caller.
        con.close()
        _migrate_under_lock(path, target_version, **backoff)
        con = _open_with_backoff(path, read_only=True, **backoff)
        ensure_vss(con)
        return con

    # Writer: hold the single-writer flock for the connection's lifetime.
    fd = os.open(lock_path(), os.O_CREAT | os.O_RDWR, 0o644)
    fcntl.flock(fd, fcntl.LOCK_EX)
    try:
        con = _open_with_backoff(path, read_only=False, **backoff)
        ensure_vss(con)
        if migrate and current_version(con) < target_version:
            apply_pending(con)
    except BaseException:
        _release_flock(fd)
        raise
    weakref.finalize(con, _release_flock, fd)
    return con
