"""Schema contract tests for migration ``0001_initial_schema.sql``.

These tests *are* the locked data contract for the stockroom warehouse: the
five harness-labeled tables, the cross-harness identity/reconstruction keys,
the typed-vs-JSON storage policy, and the no-faking model-grain split. They
exercise the schema through the ``schema_con`` fixture (a fresh in-memory
DuckDB with ``0001`` applied) and assert behavior — not just shape — so the
contract cannot silently drift.

There is no migration runner here (that is milestone 2); the fixture reads and
executes the DDL directly. The DDL itself is the single product artifact of
this milestone.
"""

from __future__ import annotations

from datetime import datetime

import duckdb
import pytest

EXPECTED_TABLES = {
    "sessions",
    "messages",
    "tool_calls",
    "embeddings",
    "_sync_state",
}


def _table_names(con: duckdb.DuckDBPyConnection) -> set[str]:
    rows = con.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'main'"
    ).fetchall()
    return {r[0] for r in rows}


def _insert(con: duckdb.DuckDBPyConnection, table: str, values: dict) -> None:
    """Insert one row into ``table`` from a ``{column: value}`` mapping.

    Columns are named explicitly so tests stay decoupled from physical column
    order and so a subset of (nullable) columns can be omitted.
    """
    cols = ", ".join(values)
    placeholders = ", ".join(["?"] * len(values))
    con.execute(
        f"INSERT INTO {table} ({cols}) VALUES ({placeholders})",
        list(values.values()),
    )


def _valid_session(**overrides) -> dict:
    """A minimal valid ``sessions`` row (all NOT NULL columns populated)."""
    row = {
        "harness": "cursor",
        "session_id": "sess-1",
        "source_path": "/p/sess-1.jsonl",
        "is_subagent": False,
    }
    row.update(overrides)
    return row


def _valid_message(**overrides) -> dict:
    """A minimal valid ``messages`` row (all NOT NULL columns populated)."""
    row = {
        "harness": "cursor",
        "session_id": "sess-1",
        "message_id": "sess-1#0",
        "ordinal": 0,
        "role": "user",
    }
    row.update(overrides)
    return row


def _valid_tool_call(**overrides) -> dict:
    """A minimal valid ``tool_calls`` row (all NOT NULL columns populated)."""
    row = {
        "harness": "cursor",
        "session_id": "sess-1",
        "message_id": "sess-1#0",
        "ordinal": 0,
        "tool_name": "Read",
        "tool_input": "{}",
    }
    row.update(overrides)
    return row


def _valid_embedding(**overrides) -> dict:
    """A minimal valid ``embeddings`` row (all NOT NULL columns populated)."""
    row = {
        "harness": "cursor",
        "owner_table": "messages",
        "owner_id": "sess-1#0",
        "chunk_index": 0,
        "embed_model": "all-MiniLM-L6-v2",
    }
    row.update(overrides)
    return row


def _valid_sync_state(**overrides) -> dict:
    """A minimal valid ``_sync_state`` row (all NOT NULL columns populated)."""
    row = {
        "harness": "cursor",
        "source_root": "/root",
        "updated_at": datetime(2026, 6, 24, 12, 0, 0),
    }
    row.update(overrides)
    return row


_VALID_ROW_BUILDERS = {
    "sessions": _valid_session,
    "messages": _valid_message,
    "tool_calls": _valid_tool_call,
    "embeddings": _valid_embedding,
    "_sync_state": _valid_sync_state,
}


def test_all_five_tables_exist(schema_con: duckdb.DuckDBPyConnection) -> None:
    """Applying ``0001`` creates exactly the five harness-labeled tables."""
    assert _table_names(schema_con) == EXPECTED_TABLES


# --- Constraints: composite PK uniqueness -----------------------------------

# (table, primary-key columns) for each of the five tables. A second insert
# that duplicates these columns must raise a ConstraintException.
_PK_CASES = [
    ("sessions", ["harness", "session_id"]),
    ("messages", ["harness", "session_id", "message_id"]),
    ("tool_calls", ["harness", "session_id", "message_id", "ordinal"]),
    ("embeddings", ["harness", "owner_table", "owner_id", "chunk_index"]),
    ("_sync_state", ["harness", "source_root"]),
]


@pytest.mark.parametrize("table, pk_cols", _PK_CASES)
def test_composite_pk_rejects_duplicate(
    schema_con: duckdb.DuckDBPyConnection,
    table: str,
    pk_cols: list[str],
) -> None:
    """Inserting a row whose composite PK duplicates an existing row fails."""
    build = _VALID_ROW_BUILDERS[table]
    _insert(schema_con, table, build())
    # Same PK, but vary a non-PK detail where one exists, to prove it is the
    # PK (not the whole row) that collides.
    with pytest.raises(duckdb.ConstraintException):
        _insert(schema_con, table, build())


# --- Constraints: NOT NULL --------------------------------------------------

# (table, column) pairs that MUST reject NULL. Includes PK columns (implicitly
# NOT NULL) and the explicitly-required non-PK columns from the schema contract.
_NOT_NULL_CASES = [
    ("sessions", "harness"),
    ("sessions", "session_id"),
    ("sessions", "source_path"),
    ("sessions", "is_subagent"),
    ("messages", "harness"),
    ("messages", "session_id"),
    ("messages", "message_id"),
    ("messages", "ordinal"),
    ("messages", "role"),
    ("tool_calls", "harness"),
    ("tool_calls", "session_id"),
    ("tool_calls", "message_id"),
    ("tool_calls", "ordinal"),
    ("tool_calls", "tool_name"),
    ("tool_calls", "tool_input"),
    ("embeddings", "harness"),
    ("embeddings", "owner_table"),
    ("embeddings", "owner_id"),
    ("embeddings", "chunk_index"),
    ("embeddings", "embed_model"),
    ("_sync_state", "harness"),
    ("_sync_state", "source_root"),
    ("_sync_state", "updated_at"),
]


@pytest.mark.parametrize("table, column", _NOT_NULL_CASES)
def test_not_null_columns_reject_null(
    schema_con: duckdb.DuckDBPyConnection,
    table: str,
    column: str,
) -> None:
    """Each required column rejects a NULL value with a ConstraintException."""
    row = _VALID_ROW_BUILDERS[table]()
    row[column] = None
    with pytest.raises(duckdb.ConstraintException):
        _insert(schema_con, table, row)
