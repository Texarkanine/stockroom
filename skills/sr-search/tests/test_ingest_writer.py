"""Persistence tests for ``stockroom.ingest.writer``.

The writer is the *only* new DB writer and the single place ingest touches the
SQL schema. It persists a :class:`NormalizedSession` via delete-then-insert by
``(harness, session_id)`` (so re-ingesting a grown file is idempotent), expands
positional identity into ``message_id = '{session_id}#{ordinal}'`` and the
matching ``parent_id``, serializes ``tool_input`` whole (no truncation), and
upserts the per-source ``_sync_state`` watermark. These tests run against the
in-memory ``migrated_con`` (the full migration chain, i.e. the current
``project_id``/``cwd`` schema the writer targets).
"""

from datetime import datetime

import duckdb

from stockroom.ingest import writer
from stockroom.ingest.model import (
    NormalizedMessage,
    NormalizedSession,
    NormalizedToolCall,
)


def _session(**overrides) -> NormalizedSession:
    """A small claude session: user -> assistant(text + one tool_use)."""
    base = NormalizedSession(
        harness="claude",
        session_id="s1",
        source_path="/p/s1.jsonl",
        cwd="/home/user/project",
        title="t",
        harness_version="2.1.0",
        started_at=datetime(2026, 1, 1, 0, 0, 0),
        ended_at=datetime(2026, 1, 1, 0, 0, 1),
        messages=[
            NormalizedMessage(ordinal=0, role="user", text="hi"),
            NormalizedMessage(
                ordinal=1,
                role="assistant",
                parent_ordinal=0,
                text="ok",
                model="claude-sonnet-4-6",
                input_tokens=10,
                output_tokens=5,
                cache_creation_tokens=0,
                cache_read_tokens=100,
                source_uuid="u-2",
                tool_calls=[
                    NormalizedToolCall(
                        ordinal=2,
                        tool_name="Read",
                        tool_input={"file_path": "/a"},
                        source_tool_use_id="toolu_1",
                    )
                ],
            ),
        ],
    )
    for key, value in overrides.items():
        setattr(base, key, value)
    return base


def _count(con: duckdb.DuckDBPyConnection, table: str) -> int:
    return con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]


def test_write_session_inserts_all_rows(
    migrated_con: duckdb.DuckDBPyConnection,
) -> None:
    """Writing a session inserts its sessions/messages/tool_calls rows."""
    writer.write_session(migrated_con, _session())
    assert _count(migrated_con, "sessions") == 1
    assert _count(migrated_con, "messages") == 2
    assert _count(migrated_con, "tool_calls") == 1


def test_write_session_expands_message_identity(
    migrated_con: duckdb.DuckDBPyConnection,
) -> None:
    """Positional ordinals expand to ``{session_id}#{ordinal}`` ids + parents."""
    writer.write_session(migrated_con, _session())
    rows = migrated_con.execute(
        "SELECT message_id, parent_id, ordinal, role "
        "FROM messages WHERE session_id = 's1' ORDER BY ordinal"
    ).fetchall()
    assert rows[0] == ("s1#0", None, 0, "user")
    assert rows[1] == ("s1#1", "s1#0", 1, "assistant")


def test_write_session_tool_call_links_and_inputs(
    migrated_con: duckdb.DuckDBPyConnection,
) -> None:
    """A tool call attaches to its turn, keeps its block-index ordinal, JSON
    input, and provenance id.
    """
    writer.write_session(migrated_con, _session())
    row = migrated_con.execute(
        "SELECT message_id, ordinal, tool_name, tool_input->>'$.file_path', "
        "source_tool_use_id FROM tool_calls WHERE session_id = 's1'"
    ).fetchone()
    assert row == ("s1#1", 2, "Read", "/a", "toolu_1")


def test_write_session_is_idempotent(
    migrated_con: duckdb.DuckDBPyConnection,
) -> None:
    """Re-writing the same session is delete-then-insert: stable counts, no PK
    violation.
    """
    writer.write_session(migrated_con, _session())
    writer.write_session(migrated_con, _session())  # must not raise
    assert _count(migrated_con, "sessions") == 1
    assert _count(migrated_con, "messages") == 2
    assert _count(migrated_con, "tool_calls") == 1


def test_write_session_reingest_reflects_new_content(
    migrated_con: duckdb.DuckDBPyConnection,
) -> None:
    """A re-ingest of a grown session replaces the old rows with the new set."""
    writer.write_session(migrated_con, _session())
    grown = _session()
    grown.messages.append(NormalizedMessage(ordinal=2, role="user", text="more"))
    writer.write_session(migrated_con, grown)
    assert _count(migrated_con, "messages") == 3


def test_write_session_persists_cursor_models_list(
    migrated_con: duckdb.DuckDBPyConnection,
) -> None:
    """A Cursor session's enriched ``models`` LIST persists natively."""
    cur = NormalizedSession(
        harness="cursor",
        session_id="c1",
        source_path="/p/c1.jsonl",
        models=["gpt-5", "claude-4.6-sonnet"],
        messages=[NormalizedMessage(ordinal=0, role="user", text="hi")],
    )
    writer.write_session(migrated_con, cur)
    models = migrated_con.execute(
        "SELECT models FROM sessions WHERE session_id = 'c1'"
    ).fetchone()[0]
    assert models == ["gpt-5", "claude-4.6-sonnet"]


def test_write_session_no_truncation_at_rest(
    migrated_con: duckdb.DuckDBPyConnection,
) -> None:
    """A large ``tool_input`` round-trips whole through the writer."""
    big = "y" * 20000
    sess = NormalizedSession(
        harness="cursor",
        session_id="c1",
        source_path="/p/c1.jsonl",
        messages=[
            NormalizedMessage(
                ordinal=0,
                role="assistant",
                tool_calls=[
                    NormalizedToolCall(
                        ordinal=0,
                        tool_name="Write",
                        tool_input={"contents": big},
                    )
                ],
            )
        ],
    )
    writer.write_session(migrated_con, sess)
    stored = migrated_con.execute(
        "SELECT tool_input->>'$.contents' FROM tool_calls WHERE session_id = 'c1'"
    ).fetchone()[0]
    assert stored == big


def test_rewriting_session_cascades_embedding_delete(
    migrated_con: duckdb.DuckDBPyConnection,
) -> None:
    """Re-writing a session drops *its* embeddings (so edits re-embed) but leaves
    other sessions' embeddings intact.

    Embeddings are derived from a session's messages; the writer's
    delete-then-insert invalidates this session's vectors in the same operation
    that rewrites its rows, so changed content is re-embedded on the next embed
    run (see ``creative-incremental-reembed-detection.md``, option B). Other
    sessions are untouched.
    """
    writer.write_session(migrated_con, _session())  # session s1: s1#0, s1#1

    def _add_embedding(owner_id: str) -> None:
        migrated_con.execute(
            "INSERT INTO embeddings "
            "(harness, owner_table, owner_id, chunk_index, embed_model, vector) "
            "VALUES ('claude', 'messages', ?, 0, 'm', ?)",
            [owner_id, [0.0] * 384],
        )

    _add_embedding("s1#0")  # belongs to the rewritten session
    _add_embedding("s2#0")  # belongs to a different session (must survive)

    writer.write_session(migrated_con, _session())  # rewrite s1

    remaining = {
        r[0]
        for r in migrated_con.execute(
            "SELECT owner_id FROM embeddings ORDER BY owner_id"
        ).fetchall()
    }
    assert remaining == {"s2#0"}


def test_update_watermark_upserts_one_row_per_source(
    migrated_con: duckdb.DuckDBPyConnection,
) -> None:
    """``update_watermark`` inserts then updates a single ``_sync_state`` row."""
    writer.update_watermark(
        migrated_con,
        harness="claude",
        source_root="/root",
        last_mtime=datetime(2026, 1, 1, 0, 0, 0),
        last_path="/root/a.jsonl",
    )
    writer.update_watermark(
        migrated_con,
        harness="claude",
        source_root="/root",
        last_mtime=datetime(2026, 1, 2, 0, 0, 0),
        last_path="/root/b.jsonl",
    )
    rows = migrated_con.execute(
        "SELECT last_mtime, last_path FROM _sync_state "
        "WHERE harness = 'claude' AND source_root = '/root'"
    ).fetchall()
    assert len(rows) == 1
    assert rows[0][0] == datetime(2026, 1, 2, 0, 0, 0)
    assert rows[0][1] == "/root/b.jsonl"
    assert migrated_con.execute("SELECT count(*) FROM _sync_state").fetchone()[0] == 1
