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
* **Copy** — :func:`copy_warehouse` leaves a verified sibling named
  :data:`COPY_FILENAME` beside an existing warehouse. The original is only
  read. No user-facing command calls it.
"""

import errno
import os
import time
from pathlib import Path
from typing import NamedTuple

import duckdb

from stockroom.migrate import (
    SCHEMA_VERSION_TABLE,
    apply_pending,
    current_version,
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

#: Sibling name a verified copy is left under, beside the original.
COPY_FILENAME = "warehouse.copy.duckdb"


class CopyError(RuntimeError):
    """A warehouse copy was refused before a sibling was built.

    Raised when the original's schema version is below
    :data:`FORMAT_BOUNDARY`. The original is left untouched and no sibling
    file is created.
    """


class CopyMismatch(CopyError):
    """The sibling's rows or catalog do not match the original.

    Raised by :func:`verify_copy`. :func:`copy_warehouse` deletes the sibling
    and its ``.wal`` before this exception leaves it.
    """


class CopyResult(NamedTuple):
    """A verified sibling left beside the original, with its measurements.

    ``path`` is the sibling. ``original_bytes`` and ``copy_bytes`` are the two
    files' sizes after verification. ``build_seconds`` covers the schema-file
    build and the row copy. ``verify_seconds`` covers the fresh read-only
    check.
    """

    path: Path
    original_bytes: int
    copy_bytes: int
    build_seconds: float
    verify_seconds: float


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


def build_warehouse(dest: Path, *, through: int | None = None) -> None:
    """Build a head warehouse at ``dest`` from the schema file, then close it.

    Connects ``dest`` (which must not exist) at :data:`STORAGE_VERSION`,
    installs the schema file, applies any later migrations, and closes. The
    close checkpoints the file; no ``dest.wal`` may remain. Then ``dest`` is
    fsynced. Does not rename or replace anything.

    ``through`` is forwarded to :func:`stockroom.migrate.apply_pending`.
    ``None`` applies every migration after the schema file. A version stops
    the run there, so the file's tables stay at that version of the chain.
    """
    if os.path.lexists(dest):
        raise _exists(dest)
    con = duckdb.connect(
        str(dest), config={"storage_compatibility_version": STORAGE_VERSION}
    )
    try:
        install_schema(con)
        apply_pending(con, through=through)
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


def copy_warehouse(original: Path) -> CopyResult:
    """Copy ``original`` into a verified newer-format sibling and leave it.

    Reads the original's schema version on a read-only connection. Below
    :data:`FORMAT_BOUNDARY`, raises :class:`CopyError` and creates nothing.
    Otherwise builds ``warehouse.copy.duckdb`` beside ``original`` from the
    schema file, migrating only through that version, replaces every base
    table with the original's rows, and checks the sibling on a fresh
    read-only connection. The original is never opened for writing. A failed
    check deletes the sibling. Success leaves the sibling and returns its
    path, both file sizes, and the build and verification times. Does not
    take the writer flock or rename the sibling onto ``original``.
    """
    version = _read_version(original)
    if version < FORMAT_BOUNDARY:
        raise CopyError(
            f"{original} is at schema version {version}, "
            f"below the format boundary {FORMAT_BOUNDARY}"
        )
    sibling = original.with_name(COPY_FILENAME)
    _remove_temp(sibling)
    build_started = time.perf_counter()
    try:
        build_warehouse(sibling, through=version)
        _replace_rows(sibling, original)
        build_seconds = time.perf_counter() - build_started
        verify_started = time.perf_counter()
        verify_copy(original, sibling)
        verify_seconds = time.perf_counter() - verify_started
    except BaseException:
        _remove_temp(sibling)
        raise
    return CopyResult(
        path=sibling,
        original_bytes=original.stat().st_size,
        copy_bytes=sibling.stat().st_size,
        build_seconds=build_seconds,
        verify_seconds=verify_seconds,
    )


def verify_copy(original: Path, copy: Path) -> None:
    """Raise :class:`CopyMismatch` when ``copy`` differs from ``original``.

    Compares every base table with ``EXCEPT ALL`` in both directions, on a
    read-only connection to ``copy`` with ``original`` attached, and only
    tables in the current database. Compares columns, constraints, indexes,
    the view name, and view columns by opening each file with nothing attached.
    Does not compare table SQL or view SQL.
    Requires zstd data segments on the two large columns of ``copy``.
    """
    _verify_rows(original, copy)
    _verify_catalog(original, copy)


def _read_version(path: Path) -> int:
    """Return ``schema_version`` from a read-only connection, then close it."""
    con = duckdb.connect(str(path), read_only=True)
    try:
        return current_version(con)
    finally:
        con.close()


def _replace_rows(sibling: Path, original: Path) -> None:
    """Replace every base table in ``sibling`` with the rows from ``original``.

    ``sibling`` was just closed by :func:`build_warehouse`. This connection
    sets no storage version. After the checkpoint, no ``.wal`` may remain.
    """
    con = duckdb.connect(str(sibling))
    try:
        con.execute("ATTACH ? AS source (READ_ONLY)", [str(original)])
        for table in _base_tables(con):
            quoted = _quote_ident(table)
            con.execute(f"DELETE FROM {quoted}")
            con.execute(f"INSERT INTO {quoted} BY NAME SELECT * FROM source.{quoted}")
        con.execute("CHECKPOINT")
    finally:
        con.close()
    wal = _wal(sibling)
    if wal.exists():
        raise RuntimeError(f"copying rows into {sibling} left {wal}")
    _fsync(sibling)


def _verify_rows(original: Path, copy: Path) -> None:
    """Raise :class:`CopyMismatch` when any base table's rows differ."""
    con = duckdb.connect(str(copy), read_only=True)
    try:
        con.execute("ATTACH ? AS source (READ_ONLY)", [str(original)])
        for table in _base_tables(con):
            quoted = _quote_ident(table)
            for statement in (
                f"SELECT * FROM {quoted} EXCEPT ALL SELECT * FROM source.{quoted}",
                f"SELECT * FROM source.{quoted} EXCEPT ALL SELECT * FROM {quoted}",
            ):
                count = con.execute(f"SELECT count(*) FROM ({statement})").fetchone()[0]
                if count:
                    raise CopyMismatch(f"{table} differs from the original")
    finally:
        con.close()


def _verify_catalog(original: Path, copy: Path) -> None:
    """Raise :class:`CopyMismatch` when the unattached catalogs differ.

    Each file is opened with nothing attached, so ``constraint_index`` is
    comparable. View SQL is not part of the catalog. Zstd data segments are
    read from ``copy`` on that same unattached connection.
    """
    original_con = duckdb.connect(str(original), read_only=True)
    try:
        original_catalog = _catalog(original_con)
    finally:
        original_con.close()
    copy_con = duckdb.connect(str(copy), read_only=True)
    try:
        copy_catalog = _catalog(copy_con)
        _require_zstd(copy_con)
    finally:
        copy_con.close()
    for part, original_rows in original_catalog.items():
        if original_rows != copy_catalog[part]:
            raise CopyMismatch(f"{part} differ from the original")


def _base_tables(con: duckdb.DuckDBPyConnection) -> list[str]:
    """Base tables of the current database only.

    After ``ATTACH``, ``duckdb_tables()`` also lists the attached file.
    """
    return [
        row[0]
        for row in con.execute(
            "SELECT table_name FROM duckdb_tables() "
            "WHERE database_name = current_database() AND schema_name = 'main' "
            "ORDER BY table_name"
        ).fetchall()
    ]


def _catalog(con: duckdb.DuckDBPyConnection) -> dict[str, list]:
    """Schema facts that must match. Table SQL is not one of them."""
    return {
        "columns": con.execute(
            "SELECT table_name, column_name, data_type, is_nullable "
            "FROM duckdb_columns() "
            "WHERE schema_name = 'main' AND internal = false "
            "ORDER BY table_name, column_index"
        ).fetchall(),
        "constraints": con.execute(
            "SELECT table_name, constraint_index, constraint_type, "
            "constraint_text, expression, constraint_column_indexes, "
            "constraint_column_names, constraint_name "
            "FROM duckdb_constraints() WHERE schema_name = 'main' "
            "ORDER BY table_name, constraint_index"
        ).fetchall(),
        "indexes": con.execute(
            "SELECT index_name, table_name, expressions FROM duckdb_indexes() "
            "WHERE schema_name = 'main' AND is_primary = false "
            "ORDER BY index_name"
        ).fetchall(),
        "views": con.execute(
            "SELECT view_name FROM duckdb_views() "
            "WHERE schema_name = 'main' AND NOT internal ORDER BY view_name"
        ).fetchall(),
        "view_columns": con.execute(
            "SELECT table_name, column_name, data_type FROM duckdb_columns() "
            "WHERE schema_name = 'main' AND table_name IN ("
            "SELECT view_name FROM duckdb_views() "
            "WHERE schema_name = 'main' AND NOT internal"
            ") ORDER BY table_name, column_index"
        ).fetchall(),
    }


def large_column_zstd_problem(con: duckdb.DuckDBPyConnection) -> str | None:
    """Return why the two large columns are not stored as zstd, or ``None``.

    ``None`` means both columns pass. An empty column has no data segment
    and passes. A populated column with no persistent data segment returns
    ``"{table}.{column} has rows and no zstd data segment"``. A persistent
    non-validity segment outside the type allow-list, or not compressed
    with ``ZSTD``, returns
    ``"{table}.{column} stored as ({segment_type}, {compression})"``.
    ``messages.text`` allows ``VARCHAR``. ``tool_calls.tool_input`` allows
    ``VARCHAR`` or ``JSON``.
    """
    specs = (
        ("messages", "text", {"VARCHAR"}),
        ("tool_calls", "tool_input", {"VARCHAR", "JSON"}),
    )
    for table, column, types in specs:
        populated = con.execute(
            f"SELECT count(*) FROM {_quote_ident(table)} "
            f"WHERE {_quote_ident(column)} IS NOT NULL"
        ).fetchone()[0]
        segments = con.execute(
            "SELECT DISTINCT segment_type, compression "
            f"FROM pragma_storage_info('{table}') "
            "WHERE column_name = ? AND segment_type != 'VALIDITY' AND persistent",
            [column],
        ).fetchall()
        if populated and not segments:
            return f"{table}.{column} has rows and no zstd data segment"
        for segment_type, compression in segments:
            if segment_type not in types or compression != "ZSTD":
                return f"{table}.{column} stored as ({segment_type}, {compression})"
    return None


def _require_zstd(con: duckdb.DuckDBPyConnection) -> None:
    """Raise :class:`CopyMismatch` when the two large columns are not zstd.

    The message is the one :func:`large_column_zstd_problem` returns.
    ``None`` raises nothing.
    """
    problem = large_column_zstd_problem(con)
    if problem is not None:
        raise CopyMismatch(problem)


def _quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'
