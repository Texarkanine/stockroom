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

import os
from pathlib import Path

#: Env var that overrides the warehouse home (used by tests to redirect away
#: from the operator's real ``~/.stockroom/``). Later milestones (ingest,
#: sr-query, dashboard) adopt the same name.
HOME_ENV_VAR = "STOCKROOM_HOME"

#: Filenames placed inside the warehouse home.
WAREHOUSE_FILENAME = "warehouse.duckdb"
LOCK_FILENAME = ".warehouse.lock"


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
