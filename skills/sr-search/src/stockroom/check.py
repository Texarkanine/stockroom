"""The background check pass: one record, then a rehearsal or a swap.

Nothing in this module is a user-facing subcommand. Importing it does not
start a pass. ``python -m stockroom.check`` spawns a detached child, and
only that child calls :func:`entry`. The record is one JSON object,
``check.json``, in the stockroom home. :func:`next_action` chooses what an
acquired pass does with that record.
"""

import argparse
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from pathlib import Path

import duckdb

from stockroom import storage
from stockroom.home import resolve_home
from stockroom.migrate import current_version
from stockroom.warehouse import LOCK_FILENAME, WAREHOUSE_FILENAME, _flock

#: Record written by this check. A different value chooses phase A again.
CHECK_VERSION = 1

#: Alarm ceiling for :func:`entry`. Four hours. :func:`run_check` does not
#: set it.
TIME_LIMIT_SECONDS = 14400

#: How long a ``rehearsed`` record of this check version waits before phase B.
PHASE_B_WAIT_SECONDS = 86400

#: How long a ``swapped`` backup stays after ``started_at``. Fourteen days.
SWAP_BACKUP_RETENTION_SECONDS = 14 * 86400

#: Sidecar file name under the stockroom home.
CHECK_RECORD_FILENAME = "check.json"

#: Free-disk floor added to twice the live-byte estimate.
DISK_MARGIN_BYTES = 64 * 1024 * 1024


def load_record(home: Path) -> dict | None:
    """Return the check record in ``home``, or ``None`` when it is missing.

    The file is ``home /`` :data:`CHECK_RECORD_FILENAME`. A missing file is
    no record. A file that is not a JSON object raises ``ValueError``.
    """
    path = home / CHECK_RECORD_FILENAME
    if not path.exists():
        return None
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} is not a JSON object")
    return value


def write_record(home: Path, record: dict) -> None:
    """Write ``record`` to ``check.json`` by renaming a temp file in ``home``.

    The temp file is fsynced, ``os.replace`` moves it onto
    :data:`CHECK_RECORD_FILENAME`, and the directory is fsynced. A crash
    leaves either the previous record or the finished one.
    """
    payload = json.dumps(record).encode("utf-8")
    fd, name = tempfile.mkstemp(dir=home, prefix=".check-", suffix=".tmp")
    try:
        os.write(fd, payload)
        os.fsync(fd)
    except BaseException:
        os.close(fd)
        os.unlink(name)
        raise
    os.close(fd)
    os.replace(name, home / CHECK_RECORD_FILENAME)
    dir_fd = os.open(home, os.O_RDONLY)
    try:
        os.fsync(dir_fd)
    finally:
        os.close(dir_fd)


def next_action(record: dict | None, *, now: float) -> str:
    """Choose what an acquired pass does with ``record`` at ``now``.

    Returns ``phase-a``, ``phase-b``, ``wait``, ``running``, ``stop``, or
    ``finish-swap``. No record, a ``skip``, or a ``check_version`` other
    than :data:`CHECK_VERSION` is ``phase-a``. ``linked`` is
    ``finish-swap``. ``swapped``, ``mismatch``, and ``already-new`` are
    ``stop``. A ``started`` entry inside ``started_at + limit_seconds`` is
    ``running``; at or past that instant it is ``stop``. A ``rehearsed``
    entry of this check version waits until
    :data:`PHASE_B_WAIT_SECONDS` have passed, then is ``phase-b``.
    """
    if record is None or record.get("check_version") != CHECK_VERSION:
        return "phase-a"
    status = record.get("status")
    if status == "linked":
        return "finish-swap"
    if status == "skip":
        return "phase-a"
    if status in {"swapped", "mismatch", "already-new"}:
        return "stop"
    if status == "started":
        if now < record["started_at"] + record["limit_seconds"]:
            return "running"
        return "stop"
    if status == "rehearsed":
        if now < record["rehearsed_at"] + PHASE_B_WAIT_SECONDS:
            return "wait"
        return "phase-b"
    raise ValueError(f"unknown check status {status!r}")


_MEASUREMENTS = (
    "original_bytes",
    "copy_bytes",
    "disk_free",
    "build_seconds",
    "verify_seconds",
    "lock_seconds",
)


def check_line(home: Path, *, now: Callable[[], float] = time.time) -> str:
    """Return the one read-only check fact for ``home``.

    ``absent`` when the record file is missing, ``unreadable`` when it is
    not the JSON object :func:`load_record` expects. A ``started`` entry
    inside its limit is ``running``; at or past the limit it is
    ``overrun``. A skip is ``skip`` plus ``reason=<skip_reason>``. Any
    other status is that word. Present measurements are appended as
    ``key=value``, then ``path=<record path>``, except for ``absent`` and
    ``unreadable``. The value has no newline. This function does not write.
    """
    path = home / CHECK_RECORD_FILENAME
    if not path.is_file():
        return "absent"
    try:
        record = load_record(home)
    except (OSError, ValueError, json.JSONDecodeError):
        return "unreadable"
    if not isinstance(record, dict):
        return "unreadable"
    current = now()
    status = record.get("status")
    if status == "started":
        word = (
            "running"
            if current < record["started_at"] + record["limit_seconds"]
            else "overrun"
        )
    else:
        word = str(status)
    parts = [word]
    if status == "skip":
        parts.append(f"reason={record.get('skip_reason')}")
    for key in _MEASUREMENTS:
        value = record.get(key)
        if value is not None:
            parts.append(f"{key}={value}")
    parts.append(f"path={path}")
    return " ".join(parts)


def entry(home: Path, *, limit_seconds: int = TIME_LIMIT_SECONDS) -> None:
    """Run one check pass under the default ``SIGALRM`` action.

    Sets the alarm, calls :func:`run_check`, and clears the alarm if the
    pass returns. Installs no handler. A pass that is still running when
    the alarm arrives dies, and the ``finally`` does not run.
    """
    signal.alarm(limit_seconds)
    try:
        run_check(home)
    finally:
        signal.alarm(0)


def run_check(
    home: Path,
    *,
    now: Callable[[], float] = time.time,
    disk_free: Callable[[Path], int] | None = None,
) -> None:
    """Take the writer flock and record a skip, or build when the file is ready.

    A missing ``home`` is left missing. A busy flock writes nothing and
    deletes nothing. ``now`` supplies the clock. ``disk_free`` supplies free
    bytes at ``home``; omitted, it is ``shutil.disk_usage(home).free``.

    The readiness ladder runs before a build, including when the stored
    record is a skip. A linked record is finished before any sibling is
    deleted, and that finish does not walk the ladder. An unexpired start
    is left alone, sibling included.
    """
    if not home.is_dir():
        return
    try:
        with _flock(home / LOCK_FILENAME, blocking=False):
            from stockroom.doctor import SWAP_BACKUP_FILENAME, live_bytes

            _acquired(
                home,
                now=now,
                disk_free=disk_free,
                live_bytes=live_bytes,
                locked_at=time.perf_counter(),
                backup_name=SWAP_BACKUP_FILENAME,
            )
    except BlockingIOError:
        return


def _acquired(
    home: Path,
    *,
    now: Callable[[], float],
    disk_free: Callable[[Path], int] | None,
    live_bytes: Callable[[duckdb.DuckDBPyConnection], int],
    locked_at: float,
    backup_name: str,
) -> None:
    """Run one pass that already holds the writer flock."""
    record = load_record(home)
    action = next_action(record, now=now())
    if action == "finish-swap" and record is not None:
        _finish_swap(home, record, backup_name=backup_name)
        return
    if action == "running":
        return
    _remove_sibling(home)
    if action == "stop" and record is not None:
        _reclaim_swap_backup(home, record, now=now(), backup_name=backup_name)
    if action in {"stop", "wait"}:
        return
    decision = _readiness(home, disk_free=disk_free, live_bytes=live_bytes)
    if decision is not None:
        try:
            write_record(home, decision)
        except OSError:
            return
        return
    if action == "phase-a":
        _phase_a(home, now=now, disk_free=disk_free, locked_at=locked_at)
    elif action == "phase-b" and record is not None:
        _phase_b(
            home,
            record,
            now=now,
            disk_free=disk_free,
            locked_at=locked_at,
            backup_name=backup_name,
        )


def _phase_a(
    home: Path,
    *,
    now: Callable[[], float],
    disk_free: Callable[[Path], int] | None,
    locked_at: float,
) -> None:
    """Rehearse a copy, record it, then delete the sibling."""
    started_at = now()
    started = _outcome("started", phase="A", started_at=started_at)
    try:
        write_record(home, started)
    except OSError:
        return
    free = disk_free(home) if disk_free is not None else shutil.disk_usage(home).free
    try:
        result = storage.copy_warehouse(home / WAREHOUSE_FILENAME)
    except storage.CopyMismatch:
        _write_outcome(home, _outcome("mismatch", phase="A", started_at=started_at))
        return
    rehearsed = _outcome("rehearsed", phase="A", started_at=started_at)
    rehearsed["rehearsed_at"] = now()
    rehearsed["original_bytes"] = result.original_bytes
    rehearsed["copy_bytes"] = result.copy_bytes
    rehearsed["disk_free"] = free
    rehearsed["build_seconds"] = result.build_seconds
    rehearsed["verify_seconds"] = result.verify_seconds
    rehearsed["lock_seconds"] = time.perf_counter() - locked_at
    if _write_outcome(home, rehearsed):
        _remove_sibling(home)


def _phase_b(
    home: Path,
    record: dict,
    *,
    now: Callable[[], float],
    disk_free: Callable[[Path], int] | None,
    locked_at: float,
    backup_name: str,
) -> None:
    """Copy again, link the original, then replace the warehouse."""
    started_at = now()
    if not _write_outcome(home, _outcome("started", phase="B", started_at=started_at)):
        return
    free = _free_bytes(home, disk_free)
    try:
        result = storage.copy_warehouse(home / WAREHOUSE_FILENAME)
    except storage.CopyMismatch:
        _write_outcome(home, _outcome("mismatch", phase="B", started_at=started_at))
        return
    original = home / WAREHOUSE_FILENAME
    original_hash = _sha256(original)
    backup = home / backup_name
    try:
        os.link(original, backup)
    except OSError:
        return
    linked = _measured(
        "linked",
        result,
        phase="B",
        started_at=started_at,
        rehearsed_at=record.get("rehearsed_at"),
        free=free,
        locked_at=locked_at,
    )
    if not _write_outcome(home, linked):
        return
    _fsync(result.path)
    _fsync(home)
    try:
        os.replace(result.path, original)
    except OSError:
        return
    if _sha256(backup) != original_hash:
        return
    swapped = dict(linked)
    swapped["status"] = "swapped"
    _write_outcome(home, swapped)


def _finish_swap(home: Path, record: dict, *, backup_name: str) -> None:
    """Finish a linked swap from the sibling, or record one that already landed.

    Does not copy, link, or walk the readiness ladder. A missing sibling
    with matching inodes leaves the record linked.
    """
    original = home / WAREHOUSE_FILENAME
    backup = home / backup_name
    sibling = home / storage.COPY_FILENAME
    if backup.stat().st_ino == original.stat().st_ino:
        if not sibling.is_file():
            return
        try:
            os.replace(sibling, original)
        except OSError:
            return
        _fsync(home)
        swapped = dict(record)
        swapped["status"] = "swapped"
        _write_outcome(home, swapped)
        return
    swapped = dict(record)
    swapped["status"] = "swapped"
    if _write_outcome(home, swapped):
        _remove_sibling(home)


def _measured(
    status: str,
    result: storage.CopyResult,
    *,
    phase: str,
    started_at: float,
    rehearsed_at: float | None,
    free: int,
    locked_at: float,
) -> dict:
    """A record carrying one copy's measurements."""
    record = _outcome(status, phase=phase, started_at=started_at)
    record["rehearsed_at"] = rehearsed_at
    record["original_bytes"] = result.original_bytes
    record["copy_bytes"] = result.copy_bytes
    record["disk_free"] = free
    record["build_seconds"] = result.build_seconds
    record["verify_seconds"] = result.verify_seconds
    record["lock_seconds"] = time.perf_counter() - locked_at
    return record


def _free_bytes(home: Path, disk_free: Callable[[Path], int] | None) -> int:
    if disk_free is not None:
        return disk_free(home)
    return shutil.disk_usage(home).free


def _sha256(path: Path) -> str:
    """Hash ``path`` in chunks so a large warehouse is not read all at once."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _fsync(path: Path) -> None:
    """Flush a file or a directory to disk."""
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _remove_sibling(home: Path) -> None:
    """Delete ``warehouse.copy.duckdb`` and its ``.wal``, if present."""
    sibling = home / storage.COPY_FILENAME
    sibling.unlink(missing_ok=True)
    sibling.with_name(sibling.name + ".wal").unlink(missing_ok=True)


def _swap_backup_due(
    record: dict | None,
    *,
    backup: Path,
    warehouse: Path,
    now: float,
) -> bool:
    """Return whether ``backup`` is a swapped file due to be unlinked.

    True only when ``record`` is check version :data:`CHECK_VERSION` with
    status ``swapped``, ``started_at`` is an int or a float and not a bool,
    ``now`` is at least :data:`SWAP_BACKUP_RETENTION_SECONDS` after
    ``started_at``, ``backup`` and ``warehouse`` are both files, and their
    inode numbers differ. ``stat`` follows links. ``OSError`` from ``stat``
    propagates. Any other input is false. This function does not unlink
    and does not write.
    """
    if not isinstance(record, dict):
        return False
    if record.get("check_version") != CHECK_VERSION:
        return False
    if record.get("status") != "swapped":
        return False
    started_at = record.get("started_at")
    if isinstance(started_at, bool) or not isinstance(started_at, (int, float)):
        return False
    if now < started_at + SWAP_BACKUP_RETENTION_SECONDS:
        return False
    if not backup.is_file() or not warehouse.is_file():
        return False
    return backup.stat().st_ino != warehouse.stat().st_ino


def _reclaim_swap_backup(
    home: Path, record: dict, *, now: float, backup_name: str
) -> None:
    """Unlink a due swap backup. The caller holds the writer flock.

    Unlinks ``home / backup_name`` only when :func:`_swap_backup_due` is
    true for ``record``, that path, and the live warehouse in ``home``.
    A missing backup stays missing. Does not write ``check.json``.
    ``OSError`` from the due check leaves the backup in place.
    """
    backup = home / backup_name
    try:
        due = _swap_backup_due(
            record,
            backup=backup,
            warehouse=home / WAREHOUSE_FILENAME,
            now=now,
        )
    except OSError:
        return
    if due:
        backup.unlink(missing_ok=True)


def _readiness(
    home: Path,
    *,
    disk_free: Callable[[Path], int] | None,
    live_bytes: Callable[[duckdb.DuckDBPyConnection], int],
) -> dict | None:
    """Return the record to write, or ``None`` when a build may start.

    Schema is read on a read-only connection. Nothing is migrated.
    """
    warehouse_file = home / WAREHOUSE_FILENAME
    if not warehouse_file.is_file():
        return _outcome("skip", skip_reason="no-warehouse")
    if warehouse_file.with_name(warehouse_file.name + ".wal").exists():
        return _outcome("skip", skip_reason="wal")
    if os.statvfs(home).f_flag & os.ST_RDONLY:
        return _outcome("skip", skip_reason="read-only")
    con = duckdb.connect(str(warehouse_file), read_only=True)
    try:
        if current_version(con) < storage.FORMAT_BOUNDARY:
            return _outcome("skip", skip_reason="below-boundary")
        tags = con.execute(
            "SELECT tags FROM duckdb_databases() "
            "WHERE database_name = current_database()"
        ).fetchone()[0]
        if (
            tags["storage_version"] == f"{storage.STORAGE_VERSION}+"
            and storage.large_column_zstd_problem(con) is None
        ):
            return _outcome("already-new")
        free = (
            disk_free(home) if disk_free is not None else shutil.disk_usage(home).free
        )
        if free < 2 * live_bytes(con) + DISK_MARGIN_BYTES:
            return _outcome("skip", skip_reason="low-disk")
    finally:
        con.close()
    return None


def _outcome(
    status: str,
    *,
    phase: str | None = None,
    started_at: float | None = None,
    skip_reason: str | None = None,
) -> dict:
    """A record with every field set, and only the outcome filled in."""
    return {
        "check_version": CHECK_VERSION,
        "status": status,
        "phase": phase,
        "started_at": started_at,
        "limit_seconds": TIME_LIMIT_SECONDS if phase is not None else None,
        "rehearsed_at": None,
        "original_bytes": None,
        "copy_bytes": None,
        "disk_free": None,
        "build_seconds": None,
        "verify_seconds": None,
        "lock_seconds": None,
        "skip_reason": skip_reason,
    }


def launch(home: Path) -> subprocess.Popen:
    """Spawn one detached foreground pass for ``home`` and return it.

    The child keeps none of this process's standard streams and starts a
    new session. This process does not wait and does not call :func:`entry`.
    The child inherits this process's environment.
    """
    return subprocess.Popen(
        [sys.executable, "-m", "stockroom.check", "--foreground", str(home)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        close_fds=True,
    )


def main(argv: list[str] | None = None) -> int:
    """Launch a detached pass, or run one when ``--foreground`` is set.

    An omitted home is the path from :func:`stockroom.home.resolve_home`.
    ``--foreground`` calls :func:`entry` in this process. Otherwise
    :func:`launch` starts the child and this process returns without waiting.
    """
    parser = argparse.ArgumentParser(prog="python -m stockroom.check")
    parser.add_argument(
        "--foreground",
        action="store_true",
        help="Run one pass in this process.",
    )
    parser.add_argument("home", nargs="?", type=Path)
    args = parser.parse_args(argv)
    home = args.home if args.home is not None else resolve_home()[0]
    if args.foreground:
        entry(home)
        return 0
    launch(home)
    return 0


def _write_outcome(home: Path, record: dict) -> bool:
    """Write ``record``. Return ``False`` when the write raises ``OSError``."""
    try:
        write_record(home, record)
    except OSError:
        return False
    return True


if __name__ == "__main__":
    raise SystemExit(main())
