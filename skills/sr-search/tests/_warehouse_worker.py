"""Subprocess worker for the warehouse concurrency tests.

Not a test module (the leading underscore keeps pytest from collecting it).
It is launched via ``sys.executable`` by the ``spawn_worker`` fixture with the
engine ``src`` on ``PYTHONPATH`` and ``STOCKROOM_HOME`` pointing at the test's
temporary warehouse home, so a child runs in a genuinely separate process and
exercises DuckDB's *cross-process* file lock (a second connection in the same
process would merely share the instance).

Commands:

* ``hold_rw <ready_file> <seconds>`` — open the warehouse read-write directly
  (simulating an in-progress migration holding the exclusive lock), signal
  readiness, hold for ``seconds``, then release.
* ``hold_ro <ready_file> <seconds>`` — same, but a shared read-only hold.
* ``migrate_report <out_file>`` — open the warehouse as a writer through the
  real chokepoint (lazy gate + flock), then write the observed schema version
  to ``out_file``. Used to race two would-be migrators.
"""

import sys
import time
from pathlib import Path

import duckdb

from stockroom import warehouse
from stockroom.migrate import current_version


def _hold(ready_file: str, seconds: str, *, read_only: bool) -> None:
    con = duckdb.connect(str(warehouse.warehouse_path()), read_only=read_only)
    try:
        Path(ready_file).write_text("ready", encoding="utf-8")
        time.sleep(float(seconds))
    finally:
        con.close()


def _migrate_report(out_file: str) -> None:
    con = warehouse.open(read_only=False)
    try:
        Path(out_file).write_text(str(current_version(con)), encoding="utf-8")
    finally:
        con.close()


def main(argv: list[str]) -> None:
    command, *rest = argv
    if command == "hold_rw":
        _hold(rest[0], rest[1], read_only=False)
    elif command == "hold_ro":
        _hold(rest[0], rest[1], read_only=True)
    elif command == "migrate_report":
        _migrate_report(rest[0])
    else:  # pragma: no cover - defensive
        raise SystemExit(f"unknown worker command: {command}")


if __name__ == "__main__":
    main(sys.argv[1:])
