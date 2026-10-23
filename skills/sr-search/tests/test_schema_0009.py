"""Contract tests for migration ``0009_drop_vector_index.sql``.

``0009`` drops ``embeddings_vector_hnsw``, the HNSW index the released
``0003`` created, from a warehouse that has it. It needs no extension and
rebuilds no table. The cumulative schema after it is ``0009_snapshot.json``:
the ``0008`` golden without the index. It is the head golden, and the frozen
schema file must give the same schema.

The chain is built in a child process that loads ``vss``
(``released_chain_file`` / ``released_chain_con``); this process never loads
it and runs no explicit ``CHECKPOINT`` on a file that still has the index.
"""

import json
import os
from pathlib import Path

import duckdb

from stockroom.migrations import discover
from test_schema_0003 import _introspect_schema

SNAPSHOT_PATH = Path(__file__).parent / "fixtures" / "schema" / "0009_snapshot.json"

INDEX_NAME = "embeddings_vector_hnsw"


def _sql(version: int) -> str:
    """Return the packaged migration SQL of exactly ``version``."""
    return {m.version: m.path for m in discover()}[version].read_text(encoding="utf-8")


def _drop(con: duckdb.DuckDBPyConnection) -> None:
    """Run the packaged ``0009`` in its own transaction, as the runner does."""
    con.execute("BEGIN TRANSACTION")
    con.execute(_sql(9))
    con.execute("COMMIT")


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


def test_0009_drops_the_index_without_vss(released_chain_file) -> None:
    """On an indexed schema-8 file, ``0009`` drops the index with no ``vss``.

    A child process builds the file with the released chain and 20 embedded
    messages. This process then runs the packaged ``0009`` inside a
    transaction on a connection that never loads ``vss``: the index is gone,
    every row stays, and ``vss`` is still not loaded.
    """
    db = released_chain_file(8, rows=20)

    con = duckdb.connect(str(db))
    try:
        before = _non_primary_indexes(con)
        _drop(con)
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


def test_0009_run_again_changes_nothing(released_chain_con) -> None:
    """R5: once the index is gone, running ``0009`` again raises nothing and changes nothing."""
    con = released_chain_con(8)
    assert _non_primary_indexes(con) == [INDEX_NAME]
    _drop(con)
    before = _introspect_schema(con)

    _drop(con)

    assert _introspect_schema(con) == before
    assert _non_primary_indexes(con) == []


def test_0009_schema_matches_0009_snapshot(released_chain_con) -> None:
    """R5: the cumulative schema after ``0009`` (no index) matches its golden.

    A deliberate schema change regenerates ``0009_snapshot.json``
    (``STOCKROOM_UPDATE_SCHEMA_GOLDEN=1``; run only this module with it, since
    the flag rewrites every golden a run touches); accidental drift fails here.
    """
    actual = _introspect_schema(released_chain_con(9))

    if os.environ.get("STOCKROOM_UPDATE_SCHEMA_GOLDEN"):
        SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
        SNAPSHOT_PATH.write_text(
            json.dumps(actual, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    assert SNAPSHOT_PATH.is_file(), f"golden schema snapshot missing: {SNAPSHOT_PATH}"
    expected = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    assert actual == expected
    assert actual["indexes"] == []
