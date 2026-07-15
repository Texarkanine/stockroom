"""Persist normalized sessions and advance the watermark.

The writer is the only new database writer in milestone 3 and the single place
ingest touches the SQL schema. It assumes a read-write ``duckdb`` connection
already positioned on the current migrated schema — the orchestrator obtains one
through the milestone-2 ``warehouse.open(read_only=False)`` chokepoint (whose
flock enforces the single-writer invariant), or a test injects an in-memory
``migrated_con``.

Two operations:

* :func:`write_session` — **delete-then-insert by ``(harness, session_id)``** so
  re-ingesting a grown or rewritten file is idempotent (no PK violation, stable
  counts). It expands the model's positional identity into the schema's
  ``message_id = '{session_id}#{ordinal}'`` and matching ``parent_id``,
  serializes each ``tool_input`` whole as JSON (no truncation at rest), and
  denormalizes the session's ``harness`` onto every child row. Before deletion,
  it carries each existing message's ``first_seen_at`` forward by deterministic
  ``message_id``; new or previously-unobserved rows seed from the session's
  ``source_mtime``. Thus ``--full`` preserves observation history, and source
  files that disappear remain untouched because ingest never calls the writer
  for undiscovered sessions. At the same pre-delete moment it compares old vs
  new message ``text`` and deletes embeddings only for removed or text-changed
  ``message_id``s (compare-and-keep), so append-only re-ingest does not wipe
  unchanged vectors.
* :func:`update_watermark` — upsert the per-``(harness, source_root)``
  ``_sync_state`` row that drives incremental discovery.
"""

import json
from datetime import datetime

import duckdb

from stockroom.ingest.model import NormalizedSession
from stockroom.ingest.paths import workspace_key_for
from stockroom.timestamps import utc_now


def _message_id(session_id: str, ordinal: int) -> str:
    """The uniform deterministic id ``'{session_id}#{ordinal}'``."""
    return f"{session_id}#{ordinal}"


def _embedding_owner_ids_to_invalidate(
    old_texts: dict[str, str | None],
    new_texts: dict[str, str | None],
) -> set[str]:
    """Return message ids whose embeddings must be deleted on session rewrite.

    An owner is invalidated when it was removed from the session or its stored
    ``text`` changed. Unchanged ids (including both-``None`` text) are kept so
    append-only re-ingest does not wipe the semantic index.
    """
    stale: set[str] = set()
    for message_id, old_text in old_texts.items():
        if message_id not in new_texts or new_texts[message_id] != old_text:
            stale.add(message_id)
    return stale


def _delete_session(
    con: duckdb.DuckDBPyConnection, harness: str, session_id: str
) -> None:
    """Remove any existing rows for ``(harness, session_id)`` across core tables.

    Deleting children first keeps the operation clean even though ``0001``
    declares no DB-level foreign keys (logical integrity is ingest-enforced).

    Embeddings are *not* blanket-cascaded here: :func:`write_session` surgically
    deletes vectors for removed or text-changed message ids before calling this
    helper, leaving unchanged owners intact for embed lag resilience.
    """
    key = [harness, session_id]
    con.execute("DELETE FROM tool_calls WHERE harness = ? AND session_id = ?", key)
    con.execute("DELETE FROM messages WHERE harness = ? AND session_id = ?", key)
    con.execute("DELETE FROM sessions WHERE harness = ? AND session_id = ?", key)


def write_session(con: duckdb.DuckDBPyConnection, session: NormalizedSession) -> None:
    """Persist one normalized session idempotently (delete-then-insert).

    Inserts the ``sessions`` row, then its ``messages`` (with expanded
    ``message_id``/``parent_id``), then their ``tool_calls`` (``tool_input``
    serialized whole as JSON). Re-running with the same ``(harness, session_id)``
    replaces the prior rows rather than colliding on the primary key while
    carrying forward each existing message's first-observation time and
    invalidating embeddings only for removed or text-changed message ids.
    """
    prior_rows = con.execute(
        "SELECT message_id, text, first_seen_at FROM messages "
        "WHERE harness = ? AND session_id = ?",
        [session.harness, session.session_id],
    ).fetchall()
    carried_first_seen = {row[0]: row[2] for row in prior_rows}
    old_texts = {row[0]: row[1] for row in prior_rows}
    new_texts = {
        _message_id(session.session_id, message.ordinal): message.text
        for message in session.messages
    }
    stale_owners = _embedding_owner_ids_to_invalidate(old_texts, new_texts)
    if stale_owners:
        con.execute(
            "DELETE FROM embeddings WHERE harness = ? AND owner_table = 'messages' "
            "AND owner_id IN (SELECT UNNEST(?::VARCHAR[]))",
            [session.harness, list(stale_owners)],
        )
    _delete_session(con, session.harness, session.session_id)

    workspace_key = workspace_key_for(
        session.harness, cwd=session.cwd, project_id=session.project_id
    )

    con.execute(
        "INSERT INTO sessions (harness, session_id, project_id, cwd, workspace_key, "
        "git_branch, source_path, is_subagent, parent_session_id, agent_id, "
        "agent_type, spawning_tool_use_id, agent_name, models, title, "
        "harness_version, started_at, ended_at, source_mtime) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            session.harness,
            session.session_id,
            session.project_id,
            session.cwd,
            workspace_key,
            session.git_branch,
            session.source_path,
            session.is_subagent,
            session.parent_session_id,
            session.agent_id,
            session.agent_type,
            session.spawning_tool_use_id,
            session.agent_name,
            session.models,
            session.title,
            session.harness_version,
            session.started_at,
            session.ended_at,
            session.source_mtime,
        ],
    )

    for message in session.messages:
        message_id = _message_id(session.session_id, message.ordinal)
        parent_id = (
            _message_id(session.session_id, message.parent_ordinal)
            if message.parent_ordinal is not None
            else None
        )
        con.execute(
            "INSERT INTO messages (harness, session_id, message_id, parent_id, "
            "ordinal, role, text, model, ts, input_tokens, output_tokens, "
            "cache_creation_tokens, cache_read_tokens, source_uuid, first_seen_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                session.harness,
                session.session_id,
                message_id,
                parent_id,
                message.ordinal,
                message.role,
                message.text,
                message.model,
                message.ts,
                message.input_tokens,
                message.output_tokens,
                message.cache_creation_tokens,
                message.cache_read_tokens,
                message.source_uuid,
                carried_first_seen.get(message_id) or session.source_mtime,
            ],
        )
        for call in message.tool_calls:
            con.execute(
                "INSERT INTO tool_calls (harness, session_id, message_id, ordinal, "
                "tool_name, tool_input, source_tool_use_id) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                [
                    session.harness,
                    session.session_id,
                    message_id,
                    call.ordinal,
                    call.tool_name,
                    json.dumps(call.tool_input, ensure_ascii=False),
                    call.source_tool_use_id,
                ],
            )


def update_watermark(
    con: duckdb.DuckDBPyConnection,
    *,
    harness: str,
    source_root: str,
    last_mtime: datetime | None,
    last_path: str | None,
    updated_at: datetime | None = None,
) -> None:
    """Upsert the ``_sync_state`` watermark for one ``(harness, source_root)``.

    Inserts the row on first sight and updates it thereafter (one row per source
    root), recording the high-water ``(last_mtime, last_path)`` and a fresh
    ``updated_at`` (defaulting to now).
    """
    con.execute(
        "INSERT INTO _sync_state (harness, source_root, last_mtime, last_path, "
        "updated_at) VALUES (?, ?, ?, ?, ?) "
        "ON CONFLICT (harness, source_root) DO UPDATE SET "
        "last_mtime = excluded.last_mtime, last_path = excluded.last_path, "
        "updated_at = excluded.updated_at",
        [
            harness,
            source_root,
            last_mtime,
            last_path,
            updated_at or utc_now(),
        ],
    )
