"""New warehouses: the frozen schema file, the builder, and creation.

A new warehouse is built from ``stockroom/schemas/schema_0009.sql`` at an
explicit storage version, never by running the released migrations, so it
loads no extension. These tests keep the schema file equal to the chain at
version 9 apart from compression, and pin how creation puts a finished file
into place without ever replacing one.
"""

import hashlib
import shutil
from pathlib import Path

import duckdb
import pytest

from _warehouse_worker import EARLY_ID, LATE_ID
from stockroom import migrate, migrations, storage, warehouse
from stockroom.migrations import discover
from test_schema_0003 import _introspect_schema

_PRODUCT_TABLES = {"sessions", "messages", "tool_calls", "embeddings", "_sync_state"}
_HEAD_VERSION = discover()[-1].version
_ZSTD_CLAUSE = " USING COMPRESSION ZSTD"


def _tables_sql(con: duckdb.DuckDBPyConnection) -> dict[str, str]:
    return dict(
        con.execute(
            "SELECT table_name, sql FROM duckdb_tables() WHERE schema_name = 'main'"
        ).fetchall()
    )


def _views_sql(con: duckdb.DuckDBPyConnection) -> dict[str, str]:
    return dict(
        con.execute(
            "SELECT view_name, sql FROM duckdb_views() "
            "WHERE schema_name = 'main' AND NOT internal"
        ).fetchall()
    )


def _constraints(con: duckdb.DuckDBPyConnection) -> list[tuple]:
    return con.execute(
        "SELECT table_name, constraint_index, constraint_type, constraint_text, "
        "expression, constraint_column_indexes, constraint_column_names, "
        "constraint_name "
        "FROM duckdb_constraints() WHERE schema_name = 'main' "
        "ORDER BY table_name, constraint_index"
    ).fetchall()


def _non_primary_indexes(con: duckdb.DuckDBPyConnection) -> list[str]:
    return [
        row[0]
        for row in con.execute(
            "SELECT index_name FROM duckdb_indexes() WHERE NOT is_primary"
        ).fetchall()
    ]


def _vss_loaded(con: duckdb.DuckDBPyConnection) -> bool:
    return con.execute(
        "SELECT loaded FROM duckdb_extensions() WHERE extension_name = 'vss'"
    ).fetchone()[0]


def _bookkeeping(con: duckdb.DuckDBPyConnection) -> list[tuple[int, str]]:
    return con.execute(
        f"SELECT version, filename FROM {migrate.SCHEMA_VERSION_TABLE} ORDER BY version"
    ).fetchall()


def _storage_tag(con: duckdb.DuckDBPyConnection) -> str:
    tags = con.execute(
        "SELECT tags FROM duckdb_databases() WHERE database_name = current_database()"
    ).fetchone()[0]
    return tags["storage_version"]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _leftovers(folder: Path) -> list[str]:
    """Names in ``folder`` that start with the temp name (the file or its ``.wal``)."""
    return sorted(
        entry.name
        for entry in folder.iterdir()
        if entry.name.startswith(storage.BUILDING_FILENAME)
    )


def _wal_path(path: Path) -> Path:
    return path.with_name(path.name + ".wal")


def _stripped_tables(con: duckdb.DuckDBPyConnection) -> dict[str, str]:
    return {
        name: sql.replace(_ZSTD_CLAUSE, "") for name, sql in _tables_sql(con).items()
    }


def _view_columns(con: duckdb.DuckDBPyConnection) -> list[tuple[str, str]]:
    return con.execute(
        "SELECT column_name, data_type FROM duckdb_columns() "
        "WHERE schema_name = 'main' AND table_name = 'session_token_usage' "
        "ORDER BY column_index"
    ).fetchall()


def _data_segments(
    con: duckdb.DuckDBPyConnection, table: str, column: str
) -> list[tuple[str, str]]:
    return con.execute(
        "SELECT DISTINCT segment_type, compression "
        f"FROM pragma_storage_info('{table}') "
        "WHERE column_name = ? AND segment_type != 'VALIDITY'",
        [column],
    ).fetchall()


def _column_names(con: duckdb.DuckDBPyConnection, table: str) -> list[str]:
    return [
        row[0]
        for row in con.execute(
            "SELECT column_name FROM duckdb_columns() "
            "WHERE schema_name = 'main' AND table_name = ? ORDER BY column_index",
            [table],
        ).fetchall()
    ]


def _message_ids(con: duckdb.DuckDBPyConnection) -> set[str]:
    return {row[0] for row in con.execute("SELECT message_id FROM messages").fetchall()}


def _migrations_plus_m10(tmp_path: Path) -> Path:
    """Packaged migrations plus ``0010_m10.sql``, which adds ``sessions.m10``."""
    folder = tmp_path / "migrations"
    folder.mkdir()
    for migration in discover():
        shutil.copyfile(migration.path, folder / migration.path.name)
    (folder / "0010_m10.sql").write_text(
        "ALTER TABLE sessions ADD COLUMN m10 TEXT;", encoding="utf-8"
    )
    return folder


def _known_backup(folder: Path) -> Path:
    backup = folder / "warehouse.issue147-swap.duckdb"
    backup.write_bytes(b"known backup bytes")
    return backup


def test_schema_file_matches_chain_at_nine(tmp_path: Path, released_chain_file) -> None:
    """S1: the schema file and the released chain at 9 give the same catalog.

    Same introspected schema, same table SQL once the zstd clause is removed,
    same view SQL, same constraints. The clause is on ``messages`` and
    ``tool_calls`` only. The chain file is built at the same storage version:
    a ``v1.0.0`` file reloads the view's SQL with different parentheses
    (measured on DuckDB 2.0.0), which is storage, not schema.
    """
    chain_db = released_chain_file(9, storage=storage.STORAGE_VERSION)
    built_db = tmp_path / "built.duckdb"
    storage.build_warehouse(built_db)

    chain = duckdb.connect(str(chain_db), read_only=True)
    try:
        chain_schema = _introspect_schema(chain)
        chain_tables = _tables_sql(chain)
        chain_views = _views_sql(chain)
        chain_constraints = _constraints(chain)
    finally:
        chain.close()
    built = duckdb.connect(str(built_db), read_only=True)
    try:
        built_schema = _introspect_schema(built)
        built_tables = _tables_sql(built)
        built_views = _views_sql(built)
        built_constraints = _constraints(built)
    finally:
        built.close()

    assert built_schema == chain_schema
    assert {
        name: sql.replace(_ZSTD_CLAUSE, "") for name, sql in built_tables.items()
    } == chain_tables
    assert built_views == chain_views
    assert set(built_views) == {"session_token_usage"}
    assert built_constraints == chain_constraints
    assert {name for name, sql in built_tables.items() if _ZSTD_CLAUSE in sql} == {
        "messages",
        "tool_calls",
    }
    assert '"text" VARCHAR USING COMPRESSION ZSTD' in built_tables["messages"]
    assert "tool_input JSON USING COMPRESSION ZSTD" in built_tables["tool_calls"]
    assert not any(_ZSTD_CLAUSE in sql for sql in chain_tables.values())


def test_install_schema_records_one_row_and_no_index(mem_con) -> None:
    """S2: one bookkeeping row naming the schema file; five tables, the view, no index."""
    storage.install_schema(mem_con)

    assert _bookkeeping(mem_con) == [(9, "schema_0009.sql")]
    assert migrate.current_version(mem_con) == 9
    assert set(_tables_sql(mem_con)) == _PRODUCT_TABLES | {"schema_version"}
    assert set(_views_sql(mem_con)) == {"session_token_usage"}
    assert _non_primary_indexes(mem_con) == []
    assert _vss_loaded(mem_con) is False


def test_install_schema_is_one_transaction(mem_con) -> None:
    """S3: a failure partway leaves no bookkeeping row and no product table.

    A ``tool_calls`` table already exists, so the schema file fails after it
    has created ``sessions`` and ``messages``; the rollback removes them.
    """
    mem_con.execute("CREATE TABLE tool_calls (x INTEGER)")

    with pytest.raises(duckdb.Error):
        storage.install_schema(mem_con)

    assert migrate.current_version(mem_con) == 0
    assert set(_tables_sql(mem_con)) == {"tool_calls"}


def test_build_warehouse_writes_a_head_file_in_the_new_format(tmp_path: Path) -> None:
    """S4: tag ``v2.0.0+``, no ``.wal``, one bookkeeping row, at the head, no index."""
    dest = tmp_path / "built.duckdb"

    storage.build_warehouse(dest)

    assert dest.is_file()
    assert not dest.with_name(dest.name + ".wal").exists()
    con = duckdb.connect(str(dest), read_only=True)
    try:
        assert _storage_tag(con) == "v2.0.0+"
        assert _bookkeeping(con) == [(9, "schema_0009.sql")]
        assert migrate.current_version(con) == _HEAD_VERSION
        assert _non_primary_indexes(con) == []
        assert _vss_loaded(con) is False
    finally:
        con.close()


def test_build_warehouse_uses_the_storage_constant(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """S5: the storage version is set explicitly, from ``STORAGE_VERSION``."""
    monkeypatch.setattr(storage, "STORAGE_VERSION", "v1.2.0")
    dest = tmp_path / "built.duckdb"

    storage.build_warehouse(dest)

    con = duckdb.connect(str(dest), read_only=True)
    try:
        assert _storage_tag(con) == "v1.2.0+"
    finally:
        con.close()


def test_built_file_stores_large_columns_with_zstd(tmp_path: Path) -> None:
    """S6: after a write and a checkpoint, both large columns' data is ``ZSTD``.

    Only data segments are checked: validity segments show ``Uncompressed``
    or ``Constant`` even under zstd.
    """
    dest = tmp_path / "built.duckdb"
    storage.build_warehouse(dest)

    con = duckdb.connect(str(dest))
    try:
        for ordinal in range(50):
            con.execute(
                "INSERT INTO messages "
                "(harness, session_id, message_id, ordinal, role, text) "
                "VALUES ('claude', 's', ?, ?, 'user', ?)",
                [f"s#{ordinal}", ordinal, f"message text {ordinal} " * 20],
            )
            con.execute(
                "INSERT INTO tool_calls "
                "(harness, session_id, message_id, ordinal, tool_name, tool_input) "
                "VALUES ('claude', 's', ?, 0, 'Read', ?)",
                [f"s#{ordinal}", f'{{"path": "/tmp/file-{ordinal}.txt"}}'],
            )
        con.execute("CHECKPOINT")
        segments = {
            column: con.execute(
                "SELECT DISTINCT segment_type, compression "
                f"FROM pragma_storage_info('{table}') "
                "WHERE column_name = ? AND segment_type != 'VALIDITY'",
                [column],
            ).fetchall()
            for table, column in (("messages", "text"), ("tool_calls", "tool_input"))
        }
    finally:
        con.close()

    assert segments["text"] == [("VARCHAR", "ZSTD")]
    assert len(segments["tool_input"]) == 1
    assert segments["tool_input"][0][0] in {"VARCHAR", "JSON"}
    assert segments["tool_input"][0][1] == "ZSTD"


def test_build_warehouse_applies_later_migrations(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """S7: a migration after 9 runs on top of the schema file, and nothing before it."""
    folder = tmp_path / "migrations"
    folder.mkdir()
    for migration in discover():
        shutil.copyfile(migration.path, folder / migration.path.name)
    (folder / "0010_m10.sql").write_text(
        "ALTER TABLE sessions ADD COLUMN m10 TEXT;", encoding="utf-8"
    )
    monkeypatch.setattr(migrations, "migrations_dir", lambda: folder)
    dest = tmp_path / "built.duckdb"

    storage.build_warehouse(dest)

    con = duckdb.connect(str(dest), read_only=True)
    try:
        assert _bookkeeping(con) == [(9, "schema_0009.sql"), (10, "0010_m10.sql")]
        columns = [
            row[0]
            for row in con.execute(
                "SELECT column_name FROM duckdb_columns() "
                "WHERE table_name = 'sessions' ORDER BY column_index"
            ).fetchall()
        ]
    finally:
        con.close()
    assert columns[-1] == "m10"


def test_create_warehouse_refuses_an_existing_file(tmp_path: Path) -> None:
    """S8: an existing file is left byte for byte, and no temp name appears."""
    path = tmp_path / "warehouse.duckdb"
    path.write_bytes(b"not a warehouse, but someone's file")
    before = _sha256(path)

    with pytest.raises(FileExistsError):
        storage.create_warehouse(path)

    assert _sha256(path) == before
    assert _leftovers(tmp_path) == []


def test_create_warehouse_removes_a_leftover_temp_file(tmp_path: Path) -> None:
    """S9: a crashed creation's temp file and ``.wal`` are removed first."""
    path = tmp_path / "warehouse.duckdb"
    temp = tmp_path / storage.BUILDING_FILENAME
    temp.write_bytes(b"half a warehouse")
    temp.with_name(temp.name + ".wal").write_bytes(b"half a wal")

    storage.create_warehouse(path)

    assert _leftovers(tmp_path) == []
    con = duckdb.connect(str(path), read_only=True)
    try:
        assert migrate.current_version(con) == _HEAD_VERSION
        assert _bookkeeping(con) == [(9, "schema_0009.sql")]
        assert _storage_tag(con) == "v2.0.0+"
    finally:
        con.close()


def test_create_warehouse_failure_leaves_no_warehouse(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """S10: a failed build leaves no warehouse and no temp name; a retry works."""
    path = tmp_path / "warehouse.duckdb"
    real_build = storage.build_warehouse

    def _failing_build(dest: Path) -> None:
        dest.write_bytes(b"partly built")
        raise RuntimeError("disk full")

    monkeypatch.setattr(storage, "build_warehouse", _failing_build)
    with pytest.raises(RuntimeError, match="disk full"):
        storage.create_warehouse(path)

    assert not path.exists()
    assert _leftovers(tmp_path) == []

    monkeypatch.setattr(storage, "build_warehouse", real_build)
    storage.create_warehouse(path)

    assert path.is_file()
    assert _leftovers(tmp_path) == []


def test_build_warehouse_stops_at_through(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``through=9`` leaves the schema-file bookkeeping and does not add ``m10``.

    The same folder without ``through`` still applies ``0010`` (see
    ``test_build_warehouse_applies_later_migrations``).
    """
    folder = _migrations_plus_m10(tmp_path)
    monkeypatch.setattr(migrations, "migrations_dir", lambda: folder)
    dest = tmp_path / "built.duckdb"

    storage.build_warehouse(dest, through=9)

    con = duckdb.connect(str(dest), read_only=True)
    try:
        assert _bookkeeping(con) == [(9, "schema_0009.sql")]
        assert "m10" not in _column_names(con, "sessions")
    finally:
        con.close()


def test_copy_warehouse_leaves_a_verified_sibling(generations_file: Path) -> None:
    """The sibling is ``warehouse.copy.duckdb``; the original and backup stay.

    The original keeps its SHA-256 and its ``v1.0.0+`` tag, and grows no
    ``.wal``. The backup's bytes stay. The sibling has no ``.wal``, is tagged
    ``v2.0.0+``, and holds both ``e#0`` and ``l#0``.
    """
    original = generations_file
    backup = _known_backup(original.parent)
    backup_bytes = backup.read_bytes()
    before = _sha256(original)

    result = storage.copy_warehouse(original)

    assert result.path == original.with_name("warehouse.copy.duckdb")
    assert result.path.is_file()
    assert _sha256(original) == before
    assert backup.read_bytes() == backup_bytes
    assert not _wal_path(original).exists()
    assert not _wal_path(backup).exists()
    assert not _wal_path(result.path).exists()
    original_con = duckdb.connect(str(original), read_only=True)
    copy_con = duckdb.connect(str(result.path), read_only=True)
    try:
        assert _storage_tag(original_con) == "v1.0.0+"
        assert _storage_tag(copy_con) == "v2.0.0+"
        assert _message_ids(copy_con) == {EARLY_ID, LATE_ID}
    finally:
        original_con.close()
        copy_con.close()


def test_copy_warehouse_rows_match_in_both_directions(generations_file: Path) -> None:
    """Every base table matches in both ``EXCEPT ALL`` directions.

    ``schema_version`` is included, so ``applied_at`` matches too. The copy's
    version-9 filename is the original's migration name, not the schema file.
    """
    original = generations_file
    backup = _known_backup(original.parent)
    result = storage.copy_warehouse(original)

    con = duckdb.connect(str(result.path), read_only=True)
    try:
        con.execute("ATTACH ? AS source (READ_ONLY)", [str(original)])
        tables = [
            row[0]
            for row in con.execute(
                "SELECT table_name FROM duckdb_tables() "
                "WHERE database_name = current_database() AND schema_name = 'main'"
            ).fetchall()
        ]
        assert "schema_version" in tables
        for table in tables:
            quoted = '"' + table.replace('"', '""') + '"'
            for statement in (
                f"SELECT * FROM {quoted} EXCEPT ALL SELECT * FROM source.{quoted}",
                f"SELECT * FROM source.{quoted} EXCEPT ALL SELECT * FROM {quoted}",
            ):
                count = con.execute(f"SELECT count(*) FROM ({statement})").fetchone()[0]
                assert count == 0, table
        filename = con.execute(
            "SELECT filename FROM schema_version WHERE version = 9"
        ).fetchone()[0]
        original_name = con.execute(
            "SELECT filename FROM source.schema_version WHERE version = 9"
        ).fetchone()[0]
    finally:
        con.close()

    assert filename == original_name == "0009_drop_vector_index.sql"
    assert backup.read_bytes() == b"known backup bytes"


def test_copy_warehouse_catalog_matches_when_each_file_is_alone(
    generations_file: Path,
) -> None:
    """Columns, keys, constraints, and table SQL match with nothing attached.

    View SQL is not compared: a ``v1.0.0`` file reloads it with different
    parentheses than a ``v2.0.0`` file. The view name and its columns match.
    """
    original = generations_file
    result = storage.copy_warehouse(original)
    original_con = duckdb.connect(str(original), read_only=True)
    copy_con = duckdb.connect(str(result.path), read_only=True)
    try:
        assert _introspect_schema(copy_con) == _introspect_schema(original_con)
        assert _constraints(copy_con) == _constraints(original_con)
        assert _stripped_tables(copy_con) == _stripped_tables(original_con)
        assert set(_views_sql(copy_con)) == {"session_token_usage"}
        assert set(_views_sql(original_con)) == {"session_token_usage"}
        assert _view_columns(copy_con) == _view_columns(original_con)
    finally:
        original_con.close()
        copy_con.close()


def test_copy_warehouse_accepts_a_154_origin_boolean_default(
    warehouse_home: Path, released_chain_154
) -> None:
    """A warehouse DuckDB 1.5.4 wrote still copies after warehouse.open migrates it to schema 9.

    The migrated sessions default is still CAST('f' AS BOOLEAN). The schema-file sibling spells that default as DEFAULT(false). copy_warehouse returns the sibling.
    """
    original = released_chain_154(8, warehouse.warehouse_path())
    assert original.is_relative_to(warehouse_home)
    con = warehouse.open(read_only=False)
    try:
        version = migrate.current_version(con)
    finally:
        con.close()
    assert version == 9

    read_only = duckdb.connect(str(original), read_only=True)
    try:
        original_sql = _tables_sql(read_only)["sessions"]
    finally:
        read_only.close()
    assert "CAST('f' AS BOOLEAN)" in original_sql

    result = storage.copy_warehouse(original)
    read_only = duckdb.connect(str(result.path), read_only=True)
    try:
        copy_sql = _tables_sql(read_only)["sessions"]
    finally:
        read_only.close()
    assert "DEFAULT(false)" in copy_sql
    assert copy_sql != original_sql


def test_copy_warehouse_stores_large_columns_as_zstd(generations_file: Path) -> None:
    """The copied text and tool input land as zstd data segments."""
    result = storage.copy_warehouse(generations_file)
    con = duckdb.connect(str(result.path), read_only=True)
    try:
        text = _data_segments(con, "messages", "text")
        tool_input = _data_segments(con, "tool_calls", "tool_input")
    finally:
        con.close()

    assert text == [("VARCHAR", "ZSTD")]
    assert len(tool_input) == 1
    assert tool_input[0][0] in {"VARCHAR", "JSON"}
    assert tool_input[0][1] == "ZSTD"


def test_copy_warehouse_reports_sizes_and_times(generations_file: Path) -> None:
    """The result's sizes are the two files, and both durations are non-negative."""
    original = generations_file
    result = storage.copy_warehouse(original)

    assert result.original_bytes == original.stat().st_size
    assert result.copy_bytes == result.path.stat().st_size
    assert result.build_seconds >= 0
    assert result.verify_seconds >= 0


def test_verify_copy_rejects_a_deleted_row(generations_file: Path) -> None:
    """Deleting ``l#0`` after a good copy makes verification raise.

    The original's SHA-256 is unchanged.
    """
    original = generations_file
    before = _sha256(original)
    result = storage.copy_warehouse(original)
    con = duckdb.connect(str(result.path))
    try:
        con.execute("DELETE FROM messages WHERE message_id = ?", [LATE_ID])
        con.execute("CHECKPOINT")
    finally:
        con.close()

    with pytest.raises(storage.CopyMismatch):
        storage.verify_copy(original, result.path)
    assert _sha256(original) == before


def test_copy_warehouse_removes_the_sibling_when_verification_fails(
    generations_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A ``CopyMismatch`` from verification deletes the sibling and its ``.wal``."""
    original = generations_file
    before = _sha256(original)

    def _mismatch(original_path: Path, copy: Path) -> None:
        _wal_path(copy).write_bytes(b"verification wal")
        raise storage.CopyMismatch("rows differ")

    monkeypatch.setattr(storage, "verify_copy", _mismatch)

    with pytest.raises(storage.CopyMismatch):
        storage.copy_warehouse(original)

    sibling = original.with_name("warehouse.copy.duckdb")
    assert not sibling.exists()
    assert not _wal_path(sibling).exists()
    assert _sha256(original) == before


def test_copy_warehouse_drops_rows_the_builder_seeded(
    generations_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Rows inserted while building the sibling are replaced by the original's.

    The double accepts ``through``, because the copy passes the original's
    schema version.
    """
    original = generations_file
    real_build = storage.build_warehouse

    def _seed(dest: Path, *, through: int | None) -> None:
        real_build(dest, through=through)
        con = duckdb.connect(str(dest))
        try:
            con.execute(
                "INSERT INTO messages "
                "(harness, session_id, message_id, ordinal, role, text) "
                "VALUES ('claude', 'seed', 'seed#0', 0, 'user', 'seeded')"
            )
        finally:
            con.close()

    monkeypatch.setattr(storage, "build_warehouse", _seed)

    result = storage.copy_warehouse(original)

    con = duckdb.connect(str(result.path), read_only=True)
    try:
        assert _message_ids(con) == {EARLY_ID, LATE_ID}
    finally:
        con.close()


def test_copy_warehouse_replaces_a_leftover_sibling(generations_file: Path) -> None:
    """A garbage sibling and its ``.wal`` are replaced by the verified copy."""
    original = generations_file
    sibling = original.with_name("warehouse.copy.duckdb")
    sibling.write_bytes(b"garbage copy")
    _wal_path(sibling).write_bytes(b"garbage wal")

    result = storage.copy_warehouse(original)

    assert result.path == sibling
    assert sibling.is_file()
    assert _sha256(sibling) != hashlib.sha256(b"garbage copy").hexdigest()
    assert not _wal_path(sibling).exists()


def test_copy_warehouse_refuses_below_the_format_boundary(
    released_chain_file,
) -> None:
    """A schema-8 file raises ``CopyError`` and nothing is written.

    The test does not checkpoint the file: it still has the HNSW index.
    """
    original = released_chain_file(8)
    before = _sha256(original)

    with pytest.raises(storage.CopyError):
        storage.copy_warehouse(original)

    sibling = original.with_name("warehouse.copy.duckdb")
    assert not sibling.exists()
    assert not _wal_path(sibling).exists()
    assert not _wal_path(original).exists()
    assert _sha256(original) == before


def test_copy_warehouse_does_not_apply_a_migration_past_the_original(
    tmp_path: Path, released_chain_file, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A migration after the original's version is not applied to the sibling."""
    folder = _migrations_plus_m10(tmp_path)
    monkeypatch.setattr(migrations, "migrations_dir", lambda: folder)
    original = released_chain_file(9, rows=1)

    result = storage.copy_warehouse(original)

    con = duckdb.connect(str(result.path), read_only=True)
    try:
        assert "m10" not in _column_names(con, "sessions")
        assert all(version != 10 for version, _filename in _bookkeeping(con))
    finally:
        con.close()
