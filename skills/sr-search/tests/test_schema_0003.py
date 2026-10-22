"""Contract tests for migration ``0003_retired.sql``.

``0003`` is retired. It once created a cosine HNSW index on
``embeddings(vector)``, which needed the ``vss`` extension. Semantic search now
ranks every vector exactly, so the file holds only comments: a new warehouse
gets no index, and the runner still records version 3, so version numbers stay
contiguous. ``0009`` drops the index from a warehouse that already has one.

``0001``/``0002`` and their golden snapshots stay frozen; this module keeps the
cumulative ``0003_snapshot.json``, whose **indexes** section is empty.
"""

import json
import os
from pathlib import Path

import duckdb

from stockroom.migrations import discover

SNAPSHOT_PATH = Path(__file__).parent / "fixtures" / "schema" / "0003_snapshot.json"


def _apply(con: duckdb.DuckDBPyConnection, version: int) -> None:
    """Execute the packaged migration of exactly ``version`` (no runner)."""
    path = next(m.path for m in discover() if m.version == version)
    con.execute(path.read_text(encoding="utf-8"))


def _apply_chain(con: duckdb.DuckDBPyConnection) -> None:
    """Apply ``0001``..``0003`` directly (no runner)."""
    for version in (1, 2, 3):
        _apply(con, version)


def test_0003_needs_no_extension_and_creates_no_index(
    mem_con: duckdb.DuckDBPyConnection,
) -> None:
    """``0001`` to ``0003`` apply on a connection that never loaded ``vss``.

    No error is raised, no non-primary index exists afterwards, and ``vss`` is
    still not loaded.
    """
    _apply_chain(mem_con)

    indexes = mem_con.execute(
        "SELECT index_name FROM duckdb_indexes() WHERE NOT is_primary"
    ).fetchall()
    assert indexes == []
    loaded = mem_con.execute(
        "SELECT loaded FROM duckdb_extensions() WHERE extension_name = 'vss'"
    ).fetchone()[0]
    assert loaded is False


# --- Cumulative schema golden snapshot (columns + PKs + indexes) ------------


def _introspect_schema(con: duckdb.DuckDBPyConnection) -> dict:
    """Introspect the applied schema into a normalized, JSON-serializable dict.

    Extends the ``0002`` shape (per-table columns in physical order + composite
    primary keys) with a top-level ``indexes`` list capturing the
    explicitly-created (non-primary) indexes — name, table, and indexed
    expressions — so a non-primary index would show in the golden. The
    runner-owned ``schema_version`` table is excluded (it is not a product
    migration artifact).
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
    """The post-``0003`` schema (columns + PKs + no indexes) byte-matches the golden.

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
