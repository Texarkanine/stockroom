"""Contract tests for migration ``0009_drop_vector_index.sql``.

``0009`` drops ``embeddings_vector_hnsw``, the HNSW index the old ``0003``
created, from a warehouse that has it. It needs no extension and rebuilds no
table. It adds no DDL, so the cumulative schema after it is the ``0008``
golden, as ``0005`` reuses the ``0004`` golden.
"""

import json
from pathlib import Path

import duckdb

from stockroom.migrations import discover
from test_schema_0003 import _introspect_schema
from test_schema_0008 import SNAPSHOT_PATH as SNAPSHOT_0008

INDEX_NAME = "embeddings_vector_hnsw"


def _sql(version: int) -> str:
    """Return the packaged migration SQL of exactly ``version``."""
    return {m.version: m.path for m in discover()}[version].read_text(encoding="utf-8")


def _apply_through(con: duckdb.DuckDBPyConnection, version: int) -> None:
    """Apply packaged migrations through ``version`` inclusive (no runner)."""
    for migration in discover():
        if migration.version > version:
            break
        con.execute(migration.path.read_text(encoding="utf-8"))


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


def test_0009_drops_the_index_without_vss(tmp_path: Path, spawn_worker) -> None:
    """On a v2.1.2-built indexed file, ``0009`` drops the index with no ``vss``.

    A child process builds the file with v2.1.2's chain and 20 embedded
    messages. This process then runs the packaged ``0009`` inside a
    transaction on a connection that never loads ``vss``: the index is gone,
    every row stays, and ``vss`` is still not loaded.
    """
    db = tmp_path / "warehouse.duckdb"
    build = spawn_worker("build_indexed", db, 20, tmp_path / "chain")
    assert build.wait(timeout=120) == 0
    drop_sql = _sql(9)

    con = duckdb.connect(str(db))
    try:
        before = _non_primary_indexes(con)
        con.execute("BEGIN TRANSACTION")
        con.execute(drop_sql)
        con.execute("COMMIT")
        after = _non_primary_indexes(con)
        messages = con.execute("SELECT count(*) FROM messages").fetchone()[0]
        embeddings = con.execute("SELECT count(*) FROM embeddings").fetchone()[0]
        loaded = _vss_loaded(con)
    finally:
        con.close()

    assert before == [INDEX_NAME]
    assert after == []
    assert (messages, embeddings) == (20, 20)
    assert loaded is False


def test_0009_without_an_index_changes_nothing(
    mem_con: duckdb.DuckDBPyConnection,
) -> None:
    """On a chain that never had the index, ``0009`` raises nothing and changes nothing."""
    _apply_through(mem_con, 8)
    before = _introspect_schema(mem_con)

    mem_con.execute(_sql(9))

    assert _introspect_schema(mem_con) == before
    assert _non_primary_indexes(mem_con) == []


def test_0009_schema_matches_0008_snapshot(
    mem_con: duckdb.DuckDBPyConnection,
) -> None:
    """The cumulative schema after ``0009`` still matches the ``0008`` golden."""
    _apply_through(mem_con, 9)
    assert 9 in {m.version for m in discover()}

    expected = json.loads(SNAPSHOT_0008.read_text(encoding="utf-8"))
    assert _introspect_schema(mem_con) == expected
