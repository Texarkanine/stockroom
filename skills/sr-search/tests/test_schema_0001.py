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

import json
from datetime import datetime
from pathlib import Path

import duckdb
import pytest

SNAPSHOT_PATH = Path(__file__).parent / "fixtures" / "schema" / "0001_snapshot.json"

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


# --- Reconstruction, threading, subagent linkage ----------------------------


def _seed_conversation(con: duckdb.DuckDBPyConnection, session_id: str = "sess-A") -> None:
    """Populate a faithful mini-conversation: user -> assistant(2 tools) -> user.

    Mirrors the empirically-observed turn shape (text precedes tools within a
    turn; an assistant turn may emit several tool_use blocks). Used to exercise
    the conversation-reconstruction and threading contract.
    """
    _insert(con, "sessions", _valid_session(harness="claude", session_id=session_id))
    _insert(
        con,
        "messages",
        _valid_message(
            harness="claude",
            session_id=session_id,
            message_id=f"{session_id}#0",
            parent_id=None,
            ordinal=0,
            role="user",
            text="please investigate",
        ),
    )
    _insert(
        con,
        "messages",
        _valid_message(
            harness="claude",
            session_id=session_id,
            message_id=f"{session_id}#1",
            parent_id=f"{session_id}#0",
            ordinal=1,
            role="assistant",
            text="let me look",
        ),
    )
    _insert(
        con,
        "messages",
        _valid_message(
            harness="claude",
            session_id=session_id,
            message_id=f"{session_id}#2",
            parent_id=f"{session_id}#1",
            ordinal=2,
            role="user",
            text="thanks",
        ),
    )
    # The assistant turn (#1) emits two tools, in block order.
    _insert(
        con,
        "tool_calls",
        _valid_tool_call(
            harness="claude",
            session_id=session_id,
            message_id=f"{session_id}#1",
            ordinal=0,
            tool_name="Read",
        ),
    )
    _insert(
        con,
        "tool_calls",
        _valid_tool_call(
            harness="claude",
            session_id=session_id,
            message_id=f"{session_id}#1",
            ordinal=1,
            tool_name="Grep",
        ),
    )


def test_messages_reconstruct_in_conversation_order(
    schema_con: duckdb.DuckDBPyConnection,
) -> None:
    """``ORDER BY ordinal`` yields the messages in conversation order."""
    _seed_conversation(schema_con)
    rows = schema_con.execute(
        "SELECT text FROM messages WHERE session_id = 'sess-A' ORDER BY ordinal"
    ).fetchall()
    assert [r[0] for r in rows] == ["please investigate", "let me look", "thanks"]


def test_tools_attach_to_their_turn_in_block_order(
    schema_con: duckdb.DuckDBPyConnection,
) -> None:
    """A turn's tool_calls attach via message_id, ordered by their own ordinal."""
    _seed_conversation(schema_con)
    rows = schema_con.execute(
        "SELECT tool_name FROM tool_calls "
        "WHERE message_id = 'sess-A#1' ORDER BY ordinal"
    ).fetchall()
    assert [r[0] for r in rows] == ["Read", "Grep"]
    # Tools attach only to the turn that emitted them.
    other = schema_con.execute(
        "SELECT count(*) FROM tool_calls WHERE message_id = 'sess-A#0'"
    ).fetchone()
    assert other[0] == 0


def test_parent_chain_threads_and_root_is_null(
    schema_con: duckdb.DuckDBPyConnection,
) -> None:
    """``parent_id`` chains messages; the root message has NULL parent_id."""
    _seed_conversation(schema_con)
    # A self-join walks the thread from each message to its parent.
    rows = schema_con.execute(
        "SELECT m.message_id, m.parent_id, p.message_id "
        "FROM messages m "
        "LEFT JOIN messages p "
        "  ON p.session_id = m.session_id AND p.message_id = m.parent_id "
        "WHERE m.session_id = 'sess-A' ORDER BY m.ordinal"
    ).fetchall()
    # root: NULL parent, no resolved parent row
    assert rows[0] == ("sess-A#0", None, None)
    # each non-root parent_id resolves to an existing message row
    assert rows[1] == ("sess-A#1", "sess-A#0", "sess-A#0")
    assert rows[2] == ("sess-A#2", "sess-A#1", "sess-A#1")


def test_subagent_links_to_parent_session(
    schema_con: duckdb.DuckDBPyConnection,
) -> None:
    """A subagent session resolves to its parent via parent_session_id."""
    _seed_conversation(schema_con, session_id="sess-A")
    _insert(
        schema_con,
        "sessions",
        _valid_session(
            harness="claude",
            session_id="sub-1",
            is_subagent=True,
            parent_session_id="sess-A",
            agent_id="agent-x",
            agent_type="explore",
            spawning_tool_use_id="toolu_abc",
        ),
    )
    row = schema_con.execute(
        "SELECT c.session_id, c.is_subagent, p.session_id "
        "FROM sessions c "
        "JOIN sessions p "
        "  ON p.harness = c.harness AND p.session_id = c.parent_session_id "
        "WHERE c.session_id = 'sub-1'"
    ).fetchone()
    assert row == ("sub-1", True, "sess-A")


# --- Model grain: each harness fills only the grain it has (no faking) -------


def test_model_grain_split_no_faking(
    schema_con: duckdb.DuckDBPyConnection,
) -> None:
    """Cursor populates session-grain ``models``; Claude populates message-grain
    ``model``. The grain a harness lacks is honestly NULL, never fabricated.
    """
    # Cursor: conversation-grained model set; per-message model is NULL.
    _insert(
        schema_con,
        "sessions",
        _valid_session(
            harness="cursor",
            session_id="cur-1",
            models=["gpt-5", "claude-4.6-sonnet"],
        ),
    )
    _insert(
        schema_con,
        "messages",
        _valid_message(
            harness="cursor",
            session_id="cur-1",
            message_id="cur-1#0",
            ordinal=0,
            role="assistant",
            model=None,
        ),
    )
    # Claude: per-message model; session-grain models is NULL.
    _insert(
        schema_con,
        "sessions",
        _valid_session(harness="claude", session_id="cla-1", models=None),
    )
    _insert(
        schema_con,
        "messages",
        _valid_message(
            harness="claude",
            session_id="cla-1",
            message_id="cla-1#0",
            ordinal=0,
            role="assistant",
            model="claude-opus-4",
        ),
    )

    cursor_sess_models, cursor_msg_model = schema_con.execute(
        "SELECT s.models, m.model "
        "FROM sessions s JOIN messages m "
        "  ON m.harness = s.harness AND m.session_id = s.session_id "
        "WHERE s.session_id = 'cur-1'"
    ).fetchone()
    assert cursor_sess_models == ["gpt-5", "claude-4.6-sonnet"]
    assert cursor_msg_model is None  # Cursor has no per-message grain

    claude_sess_models, claude_msg_model = schema_con.execute(
        "SELECT s.models, m.model "
        "FROM sessions s JOIN messages m "
        "  ON m.harness = s.harness AND m.session_id = s.session_id "
        "WHERE s.session_id = 'cla-1'"
    ).fetchone()
    assert claude_sess_models is None  # Claude has no session-grain rollup
    assert claude_msg_model == "claude-opus-4"


# --- Typed tokens, JSON, LIST, faithful capture -----------------------------


def test_token_columns_are_typed_and_aggregatable(
    schema_con: duckdb.DuckDBPyConnection,
) -> None:
    """Token columns are typed BIGINT (SUM-aggregatable); Cursor rows are NULL."""
    _insert(schema_con, "sessions", _valid_session(harness="claude", session_id="cla-1"))
    _insert(
        schema_con,
        "messages",
        _valid_message(
            harness="claude",
            session_id="cla-1",
            message_id="cla-1#0",
            ordinal=0,
            role="assistant",
            input_tokens=1000,
            output_tokens=200,
            cache_creation_tokens=50,
            cache_read_tokens=10,
        ),
    )
    _insert(
        schema_con,
        "messages",
        _valid_message(
            harness="claude",
            session_id="cla-1",
            message_id="cla-1#1",
            ordinal=1,
            role="assistant",
            input_tokens=3000,
            output_tokens=400,
            cache_creation_tokens=0,
            cache_read_tokens=900,
        ),
    )
    # Cursor message carries no token grain.
    _insert(schema_con, "sessions", _valid_session(harness="cursor", session_id="cur-1"))
    _insert(
        schema_con,
        "messages",
        _valid_message(
            harness="cursor",
            session_id="cur-1",
            message_id="cur-1#0",
            ordinal=0,
        ),
    )

    total_in, total_out = schema_con.execute(
        "SELECT SUM(input_tokens), SUM(output_tokens) "
        "FROM messages WHERE harness = 'claude'"
    ).fetchone()
    assert total_in == 4000
    assert total_out == 600

    cursor_tokens = schema_con.execute(
        "SELECT input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens "
        "FROM messages WHERE session_id = 'cur-1'"
    ).fetchone()
    assert cursor_tokens == (None, None, None, None)


def test_tool_input_json_path_extraction(
    schema_con: duckdb.DuckDBPyConnection,
) -> None:
    """``tool_input`` is queryable JSON: ``->>`` extracts top-level and nested
    values, including from an array.
    """
    _insert(schema_con, "sessions", _valid_session(harness="claude", session_id="s1"))
    _insert(
        schema_con,
        "messages",
        _valid_message(harness="claude", session_id="s1", message_id="s1#0", ordinal=0),
    )
    _insert(
        schema_con,
        "tool_calls",
        _valid_tool_call(
            harness="claude",
            session_id="s1",
            message_id="s1#0",
            ordinal=0,
            tool_name="Shell",
            tool_input='{"command": "ls", "opts": {"cwd": "/tmp"}, "args": ["-l", "-a"]}',
        ),
    )
    cmd, cwd, first_arg = schema_con.execute(
        "SELECT tool_input->>'$.command', "
        "       tool_input->>'$.opts.cwd', "
        "       tool_input->>'$.args[0]' "
        "FROM tool_calls WHERE session_id = 's1'"
    ).fetchone()
    assert cmd == "ls"
    assert cwd == "/tmp"
    assert first_arg == "-l"


def test_models_list_is_native_and_queryable(
    schema_con: duckdb.DuckDBPyConnection,
) -> None:
    """``sessions.models`` is a native LIST: ``list_contains`` + length work."""
    _insert(
        schema_con,
        "sessions",
        _valid_session(
            harness="cursor",
            session_id="cur-1",
            models=["gpt-5", "claude-4.6-sonnet", "grok-4.3"],
        ),
    )
    has_grok, n = schema_con.execute(
        "SELECT list_contains(models, 'grok-4.3'), len(models) "
        "FROM sessions WHERE session_id = 'cur-1'"
    ).fetchone()
    assert has_grok is True
    assert n == 3


def test_no_truncation_at_rest(
    schema_con: duckdb.DuckDBPyConnection,
) -> None:
    """Large ``text`` and large JSON ``tool_input`` round-trip without loss."""
    big_text = "unicode ✓ 日本語 — emoji 🚀 — " + ("x" * 8000)
    big_value = "payload-" + ("y" * 12000)
    big_input = json.dumps({"command": "echo", "blob": big_value})

    _insert(schema_con, "sessions", _valid_session(harness="cursor", session_id="s1"))
    _insert(
        schema_con,
        "messages",
        _valid_message(
            harness="cursor",
            session_id="s1",
            message_id="s1#0",
            ordinal=0,
            text=big_text,
        ),
    )
    _insert(
        schema_con,
        "tool_calls",
        _valid_tool_call(
            harness="cursor",
            session_id="s1",
            message_id="s1#0",
            ordinal=0,
            tool_input=big_input,
        ),
    )

    stored_text = schema_con.execute(
        "SELECT text FROM messages WHERE session_id = 's1'"
    ).fetchone()[0]
    assert stored_text == big_text  # TEXT round-trips byte-identical

    stored_blob = schema_con.execute(
        "SELECT tool_input->>'$.blob' FROM tool_calls WHERE session_id = 's1'"
    ).fetchone()[0]
    assert stored_blob == big_value  # JSON content preserved whole, untruncated


def test_embeddings_vector_is_fixed_384(
    schema_con: duckdb.DuckDBPyConnection,
) -> None:
    """The ``embeddings.vector`` column stores a fixed-size FLOAT[384]."""
    vec = [0.0] * 384
    _insert(
        schema_con,
        "embeddings",
        _valid_embedding(owner_id="s1#0", vector=vec),
    )
    length = schema_con.execute(
        "SELECT len(vector) FROM embeddings WHERE owner_id = 's1#0'"
    ).fetchone()[0]
    assert length == 384

    # A wrongly-sized vector is rejected by the fixed-size array type.
    with pytest.raises(duckdb.Error):
        _insert(
            schema_con,
            "embeddings",
            _valid_embedding(owner_id="s1#1", vector=[0.0] * 383),
        )


def test_harness_neutral_accepts_unknown_harness(
    schema_con: duckdb.DuckDBPyConnection,
) -> None:
    """No CHECK locks ``harness`` to a known set: a third harness inserts fine."""
    _insert(
        schema_con,
        "sessions",
        _valid_session(harness="aider", session_id="a-1"),
    )
    count = schema_con.execute(
        "SELECT count(*) FROM sessions WHERE harness = 'aider'"
    ).fetchone()[0]
    assert count == 1


# --- Pathological / edge cases ----------------------------------------------


def test_empty_string_text_is_distinct_from_null(
    schema_con: duckdb.DuckDBPyConnection,
) -> None:
    """An empty-string ``text`` is stored as '' (not coerced to NULL)."""
    _insert(schema_con, "sessions", _valid_session(harness="cursor", session_id="s1"))
    _insert(
        schema_con,
        "messages",
        _valid_message(
            harness="cursor", session_id="s1", message_id="s1#0", ordinal=0, text=""
        ),
    )
    text = schema_con.execute(
        "SELECT text FROM messages WHERE session_id = 's1'"
    ).fetchone()[0]
    assert text == ""


def test_assistant_turn_with_zero_tools(
    schema_con: duckdb.DuckDBPyConnection,
) -> None:
    """An assistant turn that emits no tools is valid (no tool_calls rows)."""
    _insert(schema_con, "sessions", _valid_session(harness="claude", session_id="s1"))
    _insert(
        schema_con,
        "messages",
        _valid_message(
            harness="claude",
            session_id="s1",
            message_id="s1#0",
            ordinal=0,
            role="assistant",
            text="no tools this turn",
        ),
    )
    n = schema_con.execute(
        "SELECT count(*) FROM tool_calls WHERE message_id = 's1#0'"
    ).fetchone()[0]
    assert n == 0


def test_many_tools_have_contiguous_ordinals(
    schema_con: duckdb.DuckDBPyConnection,
) -> None:
    """A turn with many tools stores them with contiguous 0..n ordinals."""
    _insert(schema_con, "sessions", _valid_session(harness="claude", session_id="s1"))
    _insert(
        schema_con,
        "messages",
        _valid_message(
            harness="claude",
            session_id="s1",
            message_id="s1#0",
            ordinal=0,
            role="assistant",
        ),
    )
    for i in range(6):
        _insert(
            schema_con,
            "tool_calls",
            _valid_tool_call(
                harness="claude",
                session_id="s1",
                message_id="s1#0",
                ordinal=i,
                tool_name=f"Tool{i}",
            ),
        )
    ordinals = schema_con.execute(
        "SELECT ordinal FROM tool_calls WHERE message_id = 's1#0' ORDER BY ordinal"
    ).fetchall()
    assert [r[0] for r in ordinals] == [0, 1, 2, 3, 4, 5]


def test_identical_content_gets_distinct_ids_via_ordinal(
    schema_con: duckdb.DuckDBPyConnection,
) -> None:
    """Two messages with identical text are distinct rows (ids differ by ordinal).

    This is the crux of position-derived identity: content-hash ids would
    collide here; ``{session_id}#{ordinal}`` does not.
    """
    _insert(schema_con, "sessions", _valid_session(harness="cursor", session_id="s1"))
    for i in range(2):
        _insert(
            schema_con,
            "messages",
            _valid_message(
                harness="cursor",
                session_id="s1",
                message_id=f"s1#{i}",
                ordinal=i,
                role="user",
                text="ok",
            ),
        )
    ids = schema_con.execute(
        "SELECT message_id FROM messages WHERE session_id = 's1' ORDER BY ordinal"
    ).fetchall()
    assert [r[0] for r in ids] == ["s1#0", "s1#1"]


def test_unicode_and_large_json_tool_input(
    schema_con: duckdb.DuckDBPyConnection,
) -> None:
    """A tool_input with unicode keys/values and a large array round-trips."""
    payload = {
        "questions": [{"prompt": f"質問 {i} 🚀", "id": f"q-{i}"} for i in range(200)],
        "note": "café — naïve — 日本語",
    }
    _insert(schema_con, "sessions", _valid_session(harness="cursor", session_id="s1"))
    _insert(
        schema_con,
        "messages",
        _valid_message(harness="cursor", session_id="s1", message_id="s1#0", ordinal=0),
    )
    _insert(
        schema_con,
        "tool_calls",
        _valid_tool_call(
            harness="cursor",
            session_id="s1",
            message_id="s1#0",
            ordinal=0,
            tool_name="AskQuestion",
            tool_input=json.dumps(payload, ensure_ascii=False),
        ),
    )
    note, q_count, first_prompt = schema_con.execute(
        "SELECT tool_input->>'$.note', "
        "       json_array_length(tool_input, '$.questions'), "
        "       tool_input->>'$.questions[0].prompt' "
        "FROM tool_calls WHERE session_id = 's1'"
    ).fetchone()
    assert note == "café — naïve — 日本語"
    assert q_count == 200
    assert first_prompt == "質問 0 🚀"


# --- Locked-schema golden snapshot ------------------------------------------


def _introspect_schema(con: duckdb.DuckDBPyConnection) -> dict:
    """Introspect the applied schema into a normalized, JSON-serializable dict.

    Shape: ``{table: {"columns": [{"name","type","nullable"}, ...],
    "primary_key": [col, ...]}}``. Columns are in physical declaration order;
    types are DuckDB's canonical names (so ``FLOAT[384]``, ``VARCHAR[]``,
    ``JSON`` are all pinned). This is the literal enforcement of "locked DDL":
    any schema change must consciously regenerate the golden snapshot.
    """
    schema: dict = {}
    cols = con.execute(
        "SELECT table_name, column_name, data_type, is_nullable "
        "FROM duckdb_columns() "
        "WHERE schema_name = 'main' AND internal = false "
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
        "WHERE schema_name = 'main' AND constraint_type = 'PRIMARY KEY'"
    ).fetchall()
    for table_name, pk_cols in pks:
        schema[table_name]["primary_key"] = list(pk_cols)
    return schema


def test_schema_matches_locked_snapshot(
    schema_con: duckdb.DuckDBPyConnection,
) -> None:
    """The introspected schema matches the committed golden snapshot exactly.

    This makes "locked DDL" literal: tables, column order, types, nullability,
    and composite primary keys are all frozen. A deliberate DDL change must
    regenerate ``tests/fixtures/schema/0001_snapshot.json``; an accidental one
    fails here, and hands milestone 2 a ready-made regression guard.
    """
    assert SNAPSHOT_PATH.is_file(), (
        f"golden schema snapshot missing: {SNAPSHOT_PATH}"
    )
    expected = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    actual = _introspect_schema(schema_con)
    assert actual == expected
