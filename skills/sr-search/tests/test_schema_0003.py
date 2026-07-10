"""Contract tests for migration ``0003_embeddings_hnsw_index.sql``.

``0003`` lands the deferred VSS/HNSW vector index that Phase 2 needs: a cosine
HNSW index on ``embeddings(vector)`` with experimental persistence enabled (so
deletes/inserts work against the live index). It is a *thin* migration — it
creates only the index; the ``vss`` extension is loaded by the caller
(``warehouse.ensure_vss`` at the chokepoint, or these tests directly), never by
the migration SQL, keeping the network ``INSTALL`` off the shipped DDL path (see
``creative-vss-provisioning-and-index.md``).

``0001``/``0002`` and their golden snapshots stay frozen; this module adds the
cumulative ``0003_snapshot.json`` — identical columns/PKs to ``0002`` plus a new
**indexes** section, so an otherwise column-stable migration is still a
meaningfully locked artifact.
"""

import json
import os
from pathlib import Path

import duckdb

from stockroom import warehouse
from stockroom.migrations import discover

SNAPSHOT_PATH = Path(__file__).parent / "fixtures" / "schema" / "0003_snapshot.json"

HNSW_INDEX_NAME = "embeddings_vector_hnsw"


def _apply(con: duckdb.DuckDBPyConnection, version: int) -> None:
    """Execute the packaged migration of exactly ``version`` (no runner)."""
    path = next(m.path for m in discover() if m.version == version)
    con.execute(path.read_text(encoding="utf-8"))


def _apply_chain(con: duckdb.DuckDBPyConnection) -> None:
    """Load ``vss`` then apply ``0001``..``0003`` directly (the chain head).

    ``ensure_vss`` is the precondition ``0003`` assumes (the migration SQL does
    not ``LOAD``); calling it here mirrors what the chokepoint/fixtures do.
    """
    warehouse.ensure_vss(con)
    for version in (1, 2, 3):
        _apply(con, version)


def _unit(slot: int) -> list[float]:
    """A one-hot 384-vector (1.0 at ``slot``), giving each row a distinct
    cosine *direction* (mere magnitude scaling leaves cosine unchanged).
    """
    v = [0.0] * 384
    v[slot] = 1.0
    return v


def test_0003_creates_hnsw_cosine_index(mem_con: duckdb.DuckDBPyConnection) -> None:
    """After the chain, a non-primary HNSW index sits on ``embeddings(vector)``."""
    _apply_chain(mem_con)

    rows = mem_con.execute(
        "SELECT index_name, table_name, expressions, is_primary "
        "FROM duckdb_indexes() WHERE schema_name = 'main' "
        "AND index_name = ?",
        [HNSW_INDEX_NAME],
    ).fetchall()
    assert len(rows) == 1
    index_name, table_name, expressions, is_primary = rows[0]
    assert index_name == HNSW_INDEX_NAME
    assert table_name == "embeddings"
    assert expressions == "[vector]"
    assert is_primary is False


def test_0003_index_supports_knn_and_live_delete(
    mem_con: duckdb.DuckDBPyConnection,
) -> None:
    """The live index answers cosine KNN and accepts a delete (persistence on)."""
    _apply_chain(mem_con)
    for ordinal in range(3):
        mem_con.execute(
            "INSERT INTO embeddings "
            "(harness, owner_table, owner_id, chunk_index, embed_model, vector) "
            "VALUES ('claude', 'messages', ?, 0, 'm', ?)",
            [f"s#{ordinal}", _unit(ordinal)],
        )

    nearest = mem_con.execute(
        "SELECT owner_id FROM embeddings "
        "ORDER BY array_cosine_distance(vector, ?::FLOAT[384]) LIMIT 1",
        [_unit(0)],
    ).fetchone()[0]
    assert nearest == "s#0"

    # A delete against the live HNSW index must succeed (experimental persistence).
    mem_con.execute("DELETE FROM embeddings WHERE owner_id = 's#0'")
    assert mem_con.execute("SELECT count(*) FROM embeddings").fetchone()[0] == 2


# --- Cumulative schema golden snapshot (columns + PKs + indexes) ------------


def _introspect_schema(con: duckdb.DuckDBPyConnection) -> dict:
    """Introspect the applied schema into a normalized, JSON-serializable dict.

    Extends the ``0002`` shape (per-table columns in physical order + composite
    primary keys) with a top-level ``indexes`` list capturing the
    explicitly-created (non-primary) indexes — name, table, and indexed
    expressions — so the HNSW index is a locked part of the golden. The
    runner-owned ``schema_version`` table is excluded (it is not a product
    migration artifact). The cosine *metric* is not introspectable via
    ``duckdb_indexes()``; it is verified functionally by the KNN test above.
    """
    tables: dict = {}
    cols = con.execute(
        "SELECT table_name, column_name, data_type, is_nullable "
        "FROM duckdb_columns() "
        "WHERE schema_name = 'main' AND internal = false "
        "AND table_name != 'schema_version' "
        "ORDER BY table_name, column_index"
    ).fetchall()
    for table_name, column_name, data_type, is_nullable in cols:
        entry = tables.setdefault(table_name, {"columns": [], "primary_key": []})
        entry["columns"].append(
            {"name": column_name, "type": data_type, "nullable": bool(is_nullable)}
        )
    pks = con.execute(
        "SELECT table_name, constraint_column_names "
        "FROM duckdb_constraints() "
        "WHERE schema_name = 'main' AND constraint_type = 'PRIMARY KEY' "
        "AND table_name != 'schema_version'"
    ).fetchall()
    for table_name, pk_cols in pks:
        tables[table_name]["primary_key"] = list(pk_cols)

    index_rows = con.execute(
        "SELECT index_name, table_name, expressions FROM duckdb_indexes() "
        "WHERE schema_name = 'main' AND is_primary = false "
        "AND table_name != 'schema_version' "
        "ORDER BY index_name"
    ).fetchall()
    indexes = [
        {"name": name, "table": table, "expressions": expressions}
        for name, table, expressions in index_rows
    ]
    return {"tables": tables, "indexes": indexes}


def test_migrated_schema_matches_0003_snapshot(
    mem_con: duckdb.DuckDBPyConnection,
) -> None:
    """The post-``0003`` schema (columns + PKs + indexes) byte-matches the golden.

    A deliberate schema change regenerates ``0003_snapshot.json``
    (``STOCKROOM_UPDATE_SCHEMA_GOLDEN=1``); accidental drift fails here.
    ``0001``/``0002`` snapshots stay frozen (forward-only).
    """
    _apply_chain(mem_con)
    actual = _introspect_schema(mem_con)

    if os.environ.get("STOCKROOM_UPDATE_SCHEMA_GOLDEN"):
        SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
        SNAPSHOT_PATH.write_text(
            json.dumps(actual, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    assert SNAPSHOT_PATH.is_file(), f"golden schema snapshot missing: {SNAPSHOT_PATH}"
    expected = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    assert actual == expected
