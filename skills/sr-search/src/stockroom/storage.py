"""Warehouse creation in the storage format stockroom keeps.

A new warehouse never runs the released migration chain. It is built from a
frozen schema file that holds the schema at one version of that chain
(:data:`SCHEMA_FILE_VERSION`) with no index and with zstd on the two large
text columns, at an explicit DuckDB storage version (:data:`STORAGE_VERSION`).
Migrations after that version then run as usual. The chain stays the history
for warehouses that already exist; the schema file is frozen like a released
migration (``scripts/check_released_migrations.py`` checks both).

This module owns:

* **The storage constants** — :data:`STORAGE_VERSION` and
  :data:`FORMAT_BOUNDARY`, the schema version at which a warehouse can move
  to that storage format.
* **The schema file** — :data:`SCHEMA_FILE`, recorded in ``schema_version``
  under its own name.
* **Creation** — :func:`create_warehouse` builds under a temp name
  (:data:`BUILDING_FILENAME`) beside the warehouse and renames the finished
  file into place. It never replaces a file. The caller holds the writer
  flock (:func:`stockroom.warehouse.open` does).
"""

import errno
import os
from pathlib import Path

import duckdb

from stockroom.migrate import (
    SCHEMA_VERSION_TABLE,
    apply_pending,
    ensure_schema_version_table,
)

#: DuckDB storage version every file this module builds is created with.
STORAGE_VERSION = "v2.0.0"

#: Schema version at which a warehouse can be copied into the new format.
FORMAT_BOUNDARY = 9

#: The frozen schema file new warehouses are built from.
SCHEMA_FILE = Path(__file__).parent / "schemas" / "schema_0009.sql"

#: The chain version :data:`SCHEMA_FILE` holds.
SCHEMA_FILE_VERSION = 9

#: Temp name a new warehouse is built under, beside the warehouse file.
BUILDING_FILENAME = "warehouse.building.duckdb"


def install_schema(con: duckdb.DuckDBPyConnection) -> None:
    """Create the version-9 schema on an empty connection, in one transaction.

    Creates the ``schema_version`` table, runs :data:`SCHEMA_FILE`, and
    records one row ``(9, 'schema_0009.sql')``. On any error the transaction
    rolls back, leaving no table and no row. Later migrations are the
    caller's job (:func:`stockroom.migrate.apply_pending`).
    """
    sql = SCHEMA_FILE.read_text(encoding="utf-8")
    con.execute("BEGIN TRANSACTION")
    try:
        ensure_schema_version_table(con)
        con.execute(sql)
        con.execute(
            f"INSERT INTO {SCHEMA_VERSION_TABLE} (version, filename) VALUES (?, ?)",
            [SCHEMA_FILE_VERSION, SCHEMA_FILE.name],
        )
    except Exception:
        con.execute("ROLLBACK")
        raise
    con.execute("COMMIT")


def build_warehouse(dest: Path) -> None:
    """Build a head warehouse at ``dest`` from the schema file, then close it.

    Connects ``dest`` (which must not exist) at :data:`STORAGE_VERSION`,
    installs the schema file, applies any later migrations, and closes. The
    close checkpoints the file; no ``dest.wal`` may remain. Then ``dest`` is
    fsynced. Does not rename or replace anything.
    """
    if os.path.lexists(dest):
        raise _exists(dest)
    con = duckdb.connect(
        str(dest), config={"storage_compatibility_version": STORAGE_VERSION}
    )
    try:
        install_schema(con)
        apply_pending(con)
    finally:
        con.close()
    wal = _wal(dest)
    if wal.exists():
        raise RuntimeError(f"building {dest} left {wal} after closing it")
    _fsync(dest)


def create_warehouse(path: Path) -> None:
    """Create a missing warehouse at ``path``; never replace an existing one.

    The caller holds the writer flock. Raises ``FileExistsError`` and builds
    nothing when ``path`` exists. Otherwise removes a leftover temp file
    (:data:`BUILDING_FILENAME` and its ``.wal``) from a crashed creation,
    builds the warehouse under the temp name, checks again that ``path`` does
    not exist, renames the temp file to ``path``, and fsyncs the folder. A
    crash leaves either no warehouse and a temp file, which the next creation
    removes, or the finished warehouse and no temp name.
    """
    if os.path.lexists(path):
        raise _exists(path)
    temp = path.with_name(BUILDING_FILENAME)
    _remove_temp(temp)
    try:
        build_warehouse(temp)
        if os.path.lexists(path):
            raise _exists(path)
        os.rename(temp, path)
    except BaseException:
        _remove_temp(temp)
        raise
    _fsync(path.parent)


def _wal(path: Path) -> Path:
    return path.with_name(path.name + ".wal")


def _exists(path: Path) -> FileExistsError:
    return FileExistsError(errno.EEXIST, os.strerror(errno.EEXIST), str(path))


def _remove_temp(temp: Path) -> None:
    """Remove the temp file and its ``.wal``, if present."""
    temp.unlink(missing_ok=True)
    _wal(temp).unlink(missing_ok=True)


def _fsync(path: Path) -> None:
    """Flush ``path`` (a file or a folder) to disk."""
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
