"""Contract tests for migration ``0002_workspace_identity.sql``.

``0002`` is the project's first real *schema-changing, data-preserving* forward
migration — the Phase-1 "Done When" proof, dogfooding the milestone-2 framework.
It replaces the lossy, fabricating ``sessions.project_path`` with two
single-meaning columns: ``project_id`` (the verbatim encoded project-dir slug —
the always-present grouping identity) and the re-semantic ``cwd`` (best-effort
real path, NULL when unknown). It is structural (no backfill — the slug is not
recoverable from the lossy decode), so pre-existing rows carry ``project_id IS
NULL`` until a ``--full`` re-ingest repopulates them.

``0001`` and its golden snapshot stay frozen; this module adds a *cumulative*
schema snapshot (``0002_snapshot.json``) capturing the post-``0002`` shape.
"""

import json
import os
from pathlib import Path

import duckdb

from stockroom.migrations import discover

SNAPSHOT_PATH = Path(__file__).parent / "fixtures" / "schema" / "0002_snapshot.json"


def _apply(con: duckdb.DuckDBPyConnection, version: int) -> None:
    """Execute the packaged migration of exactly ``version`` (no runner)."""
    path = next(m.path for m in discover() if m.version == version)
    con.execute(path.read_text(encoding="utf-8"))


def _sessions_columns(con: duckdb.DuckDBPyConnection) -> set[str]:
    rows = con.execute(
        "SELECT column_name FROM duckdb_columns() "
        "WHERE table_name = 'sessions' AND schema_name = 'main'"
    ).fetchall()
    return {r[0] for r in rows}


def test_0002_adds_project_id_and_drops_project_path(mem_con) -> None:
    """After ``0002`` the ``sessions`` table gains ``project_id`` and loses
    ``project_path``; ``cwd`` is retained.
    """
    _apply(mem_con, 1)
    _apply(mem_con, 2)
    cols = _sessions_columns(mem_con)
    assert "project_id" in cols
    assert "project_path" not in cols
    assert "cwd" in cols


def test_0002_preserves_existing_rows_and_children(mem_con) -> None:
    """A ``0001``-shape session (and its message) survives the migration with
    its ``cwd`` intact — the migration is data-preserving, not destructive.
    """
    _apply(mem_con, 1)
    mem_con.execute(
        "INSERT INTO sessions (harness, session_id, project_path, cwd, "
        "source_path, is_subagent) "
        "VALUES ('cursor', 's1', '/home/user/proj', '/home/user/proj', "
        "'/p/s1.jsonl', false)"
    )
    mem_con.execute(
        "INSERT INTO messages (harness, session_id, message_id, ordinal, role) "
        "VALUES ('cursor', 's1', 's1#0', 0, 'user')"
    )
    _apply(mem_con, 2)
    row = mem_con.execute(
        "SELECT session_id, cwd FROM sessions WHERE session_id = 's1'"
    ).fetchone()
    assert row == ("s1", "/home/user/proj")
    child_count = mem_con.execute(
        "SELECT count(*) FROM messages WHERE session_id = 's1'"
    ).fetchone()[0]
    assert child_count == 1


def test_0002_preexisting_project_id_is_null(mem_con) -> None:
    """A row migrated from ``0001`` has ``project_id IS NULL`` (no backfill —
    the verbatim slug is unrecoverable from the lossy old value; a ``--full``
    re-ingest repopulates it).
    """
    _apply(mem_con, 1)
    mem_con.execute(
        "INSERT INTO sessions (harness, session_id, project_path, source_path, "
        "is_subagent) VALUES ('cursor', 's1', '/home/user/proj', '/p/s1.jsonl', "
        "false)"
    )
    _apply(mem_con, 2)
    project_id = mem_con.execute(
        "SELECT project_id FROM sessions WHERE session_id = 's1'"
    ).fetchone()[0]
    assert project_id is None


# --- Cumulative schema golden snapshot --------------------------------------


def _introspect_schema(con: duckdb.DuckDBPyConnection) -> dict:
    """Introspect the applied schema into a normalized, JSON-serializable dict.

    Same shape as the ``0001`` snapshot helper (columns in physical order with
    type + nullability, plus composite primary keys), excluding the runner-owned
    ``schema_version`` bookkeeping table so the snapshot captures only the
    product data contract.
    """
    schema: dict = {}
    cols = con.execute(
        "SELECT table_name, column_name, data_type, is_nullable "
        "FROM duckdb_columns() "
        "WHERE schema_name = 'main' AND internal = false "
        "AND table_name != 'schema_version' "
        "ORDER BY table_name, column_index"
    ).fetchall()
    for table_name, column_name, data_type, is_nullable in cols:
        entry = schema.setdefault(table_name, {"columns": [], "primary_key": []})
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
        schema[table_name]["primary_key"] = list(pk_cols)
    return schema


def test_migrated_schema_matches_cumulative_snapshot(mem_con) -> None:
    """The post-``0002`` schema byte-matches the committed cumulative snapshot.

    Makes the migrated DDL literal: a deliberate schema change must regenerate
    ``tests/fixtures/schema/0002_snapshot.json``
    (``STOCKROOM_UPDATE_SCHEMA_GOLDEN=1``); an accidental drift fails here.
    ``0001_snapshot.json`` stays untouched (the forward-only invariant).
    """
    _apply(mem_con, 1)
    _apply(mem_con, 2)
    actual = _introspect_schema(mem_con)

    if os.environ.get("STOCKROOM_UPDATE_SCHEMA_GOLDEN"):
        SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
        SNAPSHOT_PATH.write_text(
            json.dumps(actual, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    assert SNAPSHOT_PATH.is_file(), f"golden schema snapshot missing: {SNAPSHOT_PATH}"
    expected = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    assert actual == expected
