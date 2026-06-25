"""The stockroom migration runner: forward-only, transactional, recorded.

This module is the *applied-state* half of the migration subsystem (discovery
— "what migrations exist" — lives in :mod:`stockroom.migrations`). It owns a
``schema_version`` bookkeeping table and applies pending migrations in
ascending version order, each in its own transaction together with its
bookkeeping row.

Key contract decisions (see
``memory-bank/active/creative/creative-warehouse-concurrency-locking.md``):

* ``schema_version`` is **runner-owned** and created via
  ``CREATE TABLE IF NOT EXISTS`` *before* any numbered migration — it is not
  part of ``0001``. This keeps the locked ``0001`` data contract (and its
  golden snapshot) free of migration bookkeeping and lets the runner answer
  "has even ``0001`` been applied?".
* The runner assumes it holds a **read-write** connection. Cross-process
  exclusivity (the flock single-writer token) is the caller's job
  (:mod:`stockroom.warehouse`); this module is pure forward-only mechanics.
* **Forward-only**: migrations are never reversed; ``apply_pending`` only ever
  moves the version up, and is a no-op when the DB is current or ahead.
"""

from pathlib import Path

import duckdb

from stockroom.migrations import discover

#: Name of the runner-owned bookkeeping table. One row per applied migration.
SCHEMA_VERSION_TABLE = "schema_version"


def ensure_schema_version_table(con: duckdb.DuckDBPyConnection) -> None:
    """Create the ``schema_version`` bookkeeping table if it does not exist.

    Idempotent (``CREATE TABLE IF NOT EXISTS``). Records, per applied
    migration: the integer ``version`` (primary key), the source ``filename``,
    and a non-NULL ``applied_at`` timestamp (defaulted to the apply time).
    """
    con.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {SCHEMA_VERSION_TABLE} (
            version    BIGINT    PRIMARY KEY,
            filename   TEXT      NOT NULL,
            applied_at TIMESTAMP NOT NULL DEFAULT current_timestamp
        )
        """
    )


def current_version(con: duckdb.DuckDBPyConnection) -> int:
    """Return the highest applied migration version, or ``0`` if none.

    Returns ``0`` in both bootstrap cases: when the ``schema_version`` table
    does not yet exist (nothing has ever been applied) and when it exists but
    is empty. Otherwise returns ``MAX(version)``.
    """
    table_exists = con.execute(
        "SELECT count(*) FROM information_schema.tables "
        "WHERE table_schema = 'main' AND table_name = ?",
        [SCHEMA_VERSION_TABLE],
    ).fetchone()[0]
    if not table_exists:
        return 0
    highest = con.execute(
        f"SELECT max(version) FROM {SCHEMA_VERSION_TABLE}"
    ).fetchone()[0]
    return int(highest) if highest is not None else 0


def apply_pending(
    con: duckdb.DuckDBPyConnection, directory: Path | None = None
) -> list[int]:
    """Apply every pending migration in ascending order; return their versions.

    Ensures the bookkeeping table exists, reads :func:`current_version`, then
    applies each discovered migration whose version exceeds it — in ascending
    order. Each migration's DDL and its ``schema_version`` insert run inside a
    single transaction, so a failure mid-migration rolls back atomically: a
    migration is applied-and-recorded, or neither (the recorded version stays
    honest). Returns ``[]`` when the DB is already current or ahead.

    Assumes a read-write connection; the caller is responsible for cross-process
    exclusivity (the warehouse flock).
    """
    ensure_schema_version_table(con)
    version = current_version(con)
    pending = [m for m in discover(directory) if m.version > version]

    applied: list[int] = []
    for migration in pending:
        sql = migration.path.read_text(encoding="utf-8")
        con.execute("BEGIN TRANSACTION")
        try:
            con.execute(sql)
            con.execute(
                f"INSERT INTO {SCHEMA_VERSION_TABLE} (version, filename) VALUES (?, ?)",
                [migration.version, migration.path.name],
            )
        except Exception:
            con.execute("ROLLBACK")
            raise
        con.execute("COMMIT")
        applied.append(migration.version)
    return applied
