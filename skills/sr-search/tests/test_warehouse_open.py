"""The warehouse-open chokepoint: path resolution, the lazy gate, and modes.

``stockroom.warehouse`` is the single contract every consumer goes through to
reach the DuckDB warehouse. These tests pin the harness-neutral home
resolution (XDG data home by default, overridable via ``STOCKROOM_HOME`` for tests),
the auto-created home directory, and — once the gate is wired — that opening a
fresh warehouse returns a ready, migrated connection while opening a current
one never re-runs the runner.
"""

import json
from pathlib import Path

import duckdb
import pytest

from _warehouse_worker import KILLED_SLOT, one_hot
from stockroom import migrate, semantic, warehouse
from stockroom.migrations import discover
from test_schema_0003 import _introspect_schema
from test_schema_0008 import SNAPSHOT_PATH
from test_semantic import _FixedEncoder

_PRODUCT_TABLES = {"sessions", "messages", "tool_calls", "embeddings", "_sync_state"}
_HEAD_VERSION = 9


def _vss_loaded(con: duckdb.DuckDBPyConnection) -> bool:
    return con.execute(
        "SELECT loaded FROM duckdb_extensions() WHERE extension_name = 'vss'"
    ).fetchone()[0]


def _non_primary_indexes(con: duckdb.DuckDBPyConnection) -> list[str]:
    return [
        row[0]
        for row in con.execute(
            "SELECT index_name FROM duckdb_indexes() WHERE NOT is_primary"
        ).fetchall()
    ]


def _counts(con: duckdb.DuckDBPyConnection) -> tuple[int, int]:
    """Return ``(messages, embeddings)`` row counts."""
    return (
        con.execute("SELECT count(*) FROM messages").fetchone()[0],
        con.execute("SELECT count(*) FROM embeddings").fetchone()[0],
    )


def _table_names(con: duckdb.DuckDBPyConnection) -> set[str]:
    return {
        r[0]
        for r in con.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'main'"
        ).fetchall()
    }


# --- path resolution + WarehouseBusyError (step 4) --------------------------


def test_warehouse_busy_error_is_an_exception() -> None:
    """``WarehouseBusyError`` is importable and is an ``Exception`` subclass."""
    assert issubclass(warehouse.WarehouseBusyError, Exception)


# --- open() lazy gate (step 6) ----------------------------------------------


def test_open_writer_on_fresh_path_returns_migrated_connection(
    warehouse_home: Path,
) -> None:
    """``open(read_only=False)`` on a brand-new path migrates and is ready."""
    con = warehouse.open(read_only=False)
    try:
        assert migrate.current_version(con) == _HEAD_VERSION
        assert _PRODUCT_TABLES <= _table_names(con)
        # The warehouse file was created at the resolved path.
        assert warehouse.warehouse_path().is_file()
    finally:
        con.close()


def test_open_reader_on_current_warehouse_returns_working_connection(
    warehouse_home: Path,
) -> None:
    """``open(read_only=True)`` on a current warehouse yields a usable RO conn."""
    warehouse.open(read_only=False).close()  # create + migrate first

    con = warehouse.open(read_only=True)
    try:
        assert migrate.current_version(con) == _HEAD_VERSION
        # A plain read works against the migrated schema.
        assert con.execute("SELECT count(*) FROM sessions").fetchone()[0] == 0
    finally:
        con.close()


def test_open_reader_on_current_warehouse_does_not_invoke_runner(
    warehouse_home: Path, monkeypatch
) -> None:
    """The double-checked gate skips the runner entirely when already current."""
    warehouse.open(read_only=False).close()  # create + migrate first

    def _must_not_run(*args, **kwargs):
        raise AssertionError("apply_pending must not run on a current warehouse")

    monkeypatch.setattr(warehouse, "apply_pending", _must_not_run)

    con = warehouse.open(read_only=True)
    try:
        assert migrate.current_version(con) == _HEAD_VERSION
    finally:
        con.close()


def test_open_and_open_current_do_not_load_vss(warehouse_home: Path) -> None:
    """Writer ``open()``, reader ``open()``, and ``open_current()`` load no ``vss``.

    Each connection is opened and closed in turn, so no two share one DuckDB
    instance and its loaded extensions.
    """
    loaded: dict[str, bool] = {}
    for name, opener in (
        ("writer", lambda: warehouse.open(read_only=False)),
        ("reader", lambda: warehouse.open(read_only=True)),
        ("open_current", warehouse.open_current),
    ):
        con = opener()
        try:
            loaded[name] = _vss_loaded(con)
        finally:
            con.close()

    assert loaded == {"writer": False, "reader": False, "open_current": False}


def test_open_with_migrate_false_skips_the_gate(
    warehouse_home: Path, monkeypatch
) -> None:
    """``migrate=False`` opens the warehouse as-is, bypassing the runner entirely."""
    warehouse.open(read_only=False).close()  # create + migrate first

    def _must_not_run(*args, **kwargs):
        raise AssertionError("the runner must not run when migrate=False")

    monkeypatch.setattr(warehouse, "apply_pending", _must_not_run)

    con = warehouse.open(read_only=True, migrate=False)
    try:
        assert con.execute("SELECT count(*) FROM sessions").fetchone()[0] == 0
    finally:
        con.close()


def test_open_current_returns_read_only_current_connection(
    warehouse_home: Path,
) -> None:
    """A current warehouse opens read-only without invoking a write path."""
    warehouse.open(read_only=False).close()

    con = warehouse.open_current()
    try:
        assert migrate.current_version(con) == _HEAD_VERSION
        with pytest.raises(duckdb.Error):
            con.execute("CREATE TABLE forbidden (id INTEGER)")
    finally:
        con.close()


def test_open_current_refuses_stale_schema_without_migrating(
    warehouse_home: Path,
) -> None:
    """A behind-head warehouse raises typed staleness and stays behind."""
    path = warehouse.warehouse_path()
    con = duckdb.connect(str(path))
    migration = next(item for item in discover() if item.version == 1)
    try:
        con.execute(migration.path.read_text(encoding="utf-8"))
        migrate.ensure_schema_version_table(con)
        con.execute(
            f"INSERT INTO {migrate.SCHEMA_VERSION_TABLE} (version, filename) "
            "VALUES (1, ?)",
            [migration.path.name],
        )
    finally:
        con.close()

    with pytest.raises(warehouse.WarehouseStaleError) as caught:
        warehouse.open_current()
    assert caught.value.current == 1
    assert caught.value.latest == _HEAD_VERSION
    assert "stockroom migrate" in str(caught.value)

    con = duckdb.connect(str(path), read_only=True)
    try:
        assert migrate.current_version(con) == 1
        assert "source_mtime" not in {
            row[0]
            for row in con.execute(
                "SELECT column_name FROM duckdb_columns() WHERE table_name = 'sessions'"
            ).fetchall()
        }
    finally:
        con.close()


def test_schema_one_v1_file_migrates_to_head_and_keeps_storage_tag(
    warehouse_home: Path,
) -> None:
    """A ``v1.0.0+`` file an older release left at schema 1 migrates and keeps its tag.

    Every release before the DuckDB 2.0 move pinned DuckDB 1.5.4, so a warehouse
    in the wild is storage ``v1.0.0+`` at any schema version. Opening one
    read-write must migrate it to head without rewriting its storage format:
    the tag stays ``v1.0.0+`` until a deliberate rewrite changes it.
    """
    path = warehouse.warehouse_path()
    con = duckdb.connect(str(path), config={"storage_compatibility_version": "v1.0.0"})
    migration = next(item for item in discover() if item.version == 1)
    try:
        con.execute(migration.path.read_text(encoding="utf-8"))
        migrate.ensure_schema_version_table(con)
        con.execute(
            f"INSERT INTO {migrate.SCHEMA_VERSION_TABLE} (version, filename) "
            "VALUES (1, ?)",
            [migration.path.name],
        )
    finally:
        con.close()

    con = warehouse.open(read_only=False)
    try:
        assert migrate.current_version(con) == _HEAD_VERSION
        tags = con.execute(
            "SELECT tags FROM duckdb_databases() "
            "WHERE database_name = current_database()"
        ).fetchone()[0]
        assert tags["storage_version"] == "v1.0.0+"
    finally:
        con.close()


# --- radical-innovation guard: the framework yields exactly the locked DDL --


def test_migrated_warehouse_matches_locked_snapshot(warehouse_home: Path) -> None:
    """A freshly opened warehouse's product schema byte-matches the head snapshot.

    Reuses the schema-introspection helper against the *cumulative* post-``0008``
    golden (``0008_snapshot.json``: columns + PKs + an empty index list; the
    VIEW ``session_token_usage`` appears via ``duckdb_columns``). The
    runner-owned ``schema_version`` bookkeeping table is excluded by the helper
    (it is not part of any product migration), proving the migration framework
    produces precisely the locked product DDL at the chain head: opening the
    warehouse yields the current locked schema.
    """
    con = warehouse.open(read_only=False)
    try:
        schema = _introspect_schema(con)
    finally:
        con.close()

    expected = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    assert schema == expected


# --- no vector index ------------------------------------------------------------


def test_new_warehouse_has_no_vector_index(warehouse_home: Path) -> None:
    """A warehouse that ``open()`` creates has no non-primary index."""
    con = warehouse.open(read_only=False)
    try:
        indexes = con.execute(
            "SELECT index_name FROM duckdb_indexes() WHERE NOT is_primary"
        ).fetchall()
    finally:
        con.close()

    assert indexes == []


# --- old indexed warehouses ----------------------------------------------------


def test_schema_eight_indexed_warehouse_with_killed_embed_wal_migrates_to_head(
    warehouse_home: Path, tmp_path: Path, spawn_worker, wait_for_sentinel
) -> None:
    """A schema-8 indexed file with a killed embed's ``.wal`` migrates with every row.

    One child builds a ``v1.0.0`` file at schema 8 with the HNSW index and 20
    embedded messages. A second child, with ``vss`` loaded, inserts message
    ``k#0`` and its embedding, commits, and is killed. The ``.wal`` exists.
    Then ``open(read_only=False)`` here migrates it to head: no index, no
    ``vss``, 21 messages and 21 embeddings, ``k#0`` found first by its own
    vector, a full ``limit=21`` result, and no ``.wal`` after close.
    """
    db = warehouse.warehouse_path()
    wal = db.with_name(db.name + ".wal")
    build = spawn_worker("build_indexed", db, 20, tmp_path / "chain")
    assert build.wait(timeout=120) == 0
    ready = tmp_path / "inserted"
    embedder = spawn_worker("insert_and_hang", db, ready)
    wait_for_sentinel(ready, timeout=60)
    embedder.kill()
    embedder.wait()
    assert wal.exists()

    con = warehouse.open(read_only=False)
    try:
        version = migrate.current_version(con)
        indexes = _non_primary_indexes(con)
        loaded = _vss_loaded(con)
        counts = _counts(con)
        encoder = _FixedEncoder(one_hot(KILLED_SLOT))
        nearest = semantic.run_semantic_search(
            "the killed row", encoder, con=con, query_prefix="", limit=1
        )
        everything = semantic.run_semantic_search(
            "the killed row", encoder, con=con, query_prefix="", limit=21
        )
    finally:
        con.close()

    assert version == _HEAD_VERSION
    assert indexes == []
    assert loaded is False
    assert counts == (21, 21)
    assert [hit.message_id for hit in nearest] == ["k#0"]
    assert len(everything) == 21
    assert not wal.exists()


def test_writer_killed_after_index_drop_reopens_at_head(
    warehouse_home: Path, tmp_path: Path, spawn_worker, wait_for_sentinel
) -> None:
    """A migrator killed after it committed ``0009`` leaves a file that reopens at head.

    A child builds a clean indexed schema-8 file. A second child opens it as a
    writer through ``open()``, which migrates, then is killed before it closes.
    The ``.wal`` exists. Then ``open()`` here gives head, no index, and every
    row.
    """
    db = warehouse.warehouse_path()
    wal = db.with_name(db.name + ".wal")
    build = spawn_worker("build_indexed", db, 20, tmp_path / "chain")
    assert build.wait(timeout=120) == 0
    ready = tmp_path / "migrated"
    migrator = spawn_worker("migrate_and_hang", ready)
    wait_for_sentinel(ready, timeout=60)
    migrator.kill()
    migrator.wait()
    assert ready.read_text(encoding="utf-8") == str(_HEAD_VERSION)
    assert wal.exists()

    con = warehouse.open()
    try:
        version = migrate.current_version(con)
        indexes = _non_primary_indexes(con)
        counts = _counts(con)
    finally:
        con.close()

    assert version == _HEAD_VERSION
    assert indexes == []
    assert counts == (20, 20)
