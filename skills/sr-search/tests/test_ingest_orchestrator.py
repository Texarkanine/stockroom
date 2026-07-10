"""Integration tests for the ingest orchestrator (``stockroom.ingest.ingest``).

These wire the whole ETL together over the committed fixture corpus, through an
injected in-memory ``migrated_con`` connection (the full migration chain, i.e.
the current ``project_id``/``cwd`` schema; no real warehouse needed), with the
two harness roots pointed at the fixtures and the synthetic enrichment DB
supplied. They assert the cross-table / cross-file invariants the milestone
promises — subagent<->parent linkage, inputs-only, no truncation, dense
ordinals, harness labels, idempotent incremental no-op, and the workspace
``project_id``/``cwd`` contract (verbatim slug; honest cwd recovery or NULL with
no fabrication) — and lock the entire reconstruction output against a committed
golden snapshot.

The golden file is produced by this test's *own* dump helper (set
``STOCKROOM_UPDATE_INGEST_GOLDEN=1`` to regenerate), so the generator and the
assertion can never diverge — the milestone-3 analogue of the m1 schema
snapshot.
"""

import json
import os
from datetime import datetime
from pathlib import Path

import duckdb
import pytest

from stockroom import ingest
from stockroom.ingest.paths import encode_for

GOLDEN_PATH = Path(__file__).parent / "fixtures" / "ingest" / "expected_rows.json"


@pytest.fixture
def fixture_roots(
    monkeypatch: pytest.MonkeyPatch, cursor_root: Path, claude_root: Path
) -> None:
    """Point the ingest discovery roots at the committed fixtures."""
    monkeypatch.setenv("STOCKROOM_CURSOR_ROOT", str(cursor_root))
    monkeypatch.setenv("STOCKROOM_CLAUDE_ROOT", str(claude_root))


def _count(con: duckdb.DuckDBPyConnection, table: str) -> int:
    return con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]


def _full_ingest(
    con: duckdb.DuckDBPyConnection, ai_tracking_db: Path
) -> ingest.IngestSummary:
    return ingest.ingest(full=True, con=con, ai_tracking_db=ai_tracking_db)


def test_full_ingest_summary_matches_table_counts(
    migrated_con: duckdb.DuckDBPyConnection,
    fixture_roots: None,
    ai_tracking_db: Path,
) -> None:
    """A full fixture ingest populates all tables and the summary counts equal
    the actual table row counts.
    """
    summary = _full_ingest(migrated_con, ai_tracking_db)
    assert summary.sessions == _count(migrated_con, "sessions")
    assert summary.messages == _count(migrated_con, "messages")
    assert summary.tool_calls == _count(migrated_con, "tool_calls")
    # Both harnesses contributed.
    assert summary.by_harness["cursor"].sessions > 0
    assert summary.by_harness["claude"].sessions > 0


def test_harness_filter_writes_only_selected(
    migrated_con: duckdb.DuckDBPyConnection,
    fixture_roots: None,
    ai_tracking_db: Path,
) -> None:
    """``harness='claude'`` ingests only Claude rows."""
    ingest.ingest(
        full=True, con=migrated_con, harness="claude", ai_tracking_db=ai_tracking_db
    )
    harnesses = {
        r[0]
        for r in migrated_con.execute(
            "SELECT DISTINCT harness FROM sessions"
        ).fetchall()
    }
    assert harnesses == {"claude"}


def test_second_incremental_ingest_is_noop(
    migrated_con: duckdb.DuckDBPyConnection,
    fixture_roots: None,
    ai_tracking_db: Path,
) -> None:
    """After a full ingest, an incremental run writes no new rows (watermark)."""
    _full_ingest(migrated_con, ai_tracking_db)
    before = {
        t: _count(migrated_con, t) for t in ("sessions", "messages", "tool_calls")
    }
    summary = ingest.ingest(full=False, con=migrated_con, ai_tracking_db=ai_tracking_db)
    after = {t: _count(migrated_con, t) for t in ("sessions", "messages", "tool_calls")}
    assert after == before
    assert summary.sessions == 0


def test_subagents_link_to_parents_across_the_run(
    migrated_con: duckdb.DuckDBPyConnection,
    fixture_roots: None,
    ai_tracking_db: Path,
) -> None:
    """Every subagent session resolves to an existing parent session row, and
    each Claude subagent's spawn id joins a parent tool-call provenance id.
    """
    _full_ingest(migrated_con, ai_tracking_db)
    # Subagent -> parent session join holds for both harnesses.
    orphans = migrated_con.execute(
        "SELECT c.session_id FROM sessions c "
        "LEFT JOIN sessions p "
        "  ON p.harness = c.harness AND p.session_id = c.parent_session_id "
        "WHERE c.is_subagent AND p.session_id IS NULL"
    ).fetchall()
    assert orphans == []
    # The Claude subagent's spawning_tool_use_id joins its parent's Task call.
    joined = migrated_con.execute(
        "SELECT c.session_id FROM sessions c "
        "JOIN tool_calls t "
        "  ON t.harness = c.harness "
        "  AND t.session_id = c.parent_session_id "
        "  AND t.source_tool_use_id = c.spawning_tool_use_id "
        "WHERE c.harness = 'claude' AND c.is_subagent"
    ).fetchall()
    assert len(joined) == 1


def test_inputs_only_no_tool_result_text_stored(
    migrated_con: duckdb.DuckDBPyConnection,
    fixture_roots: None,
    ai_tracking_db: Path,
) -> None:
    """No dropped tool_result output text leaks into messages (inputs only)."""
    _full_ingest(migrated_con, ai_tracking_db)
    leaked = migrated_con.execute(
        "SELECT count(*) FROM messages WHERE text LIKE '%auth/middleware.py%'"
    ).fetchone()[0]
    assert leaked == 0


def test_ordinals_are_dense_per_session(
    migrated_con: duckdb.DuckDBPyConnection,
    fixture_roots: None,
    ai_tracking_db: Path,
) -> None:
    """Each session's message ordinals are a dense 0..n-1 run."""
    _full_ingest(migrated_con, ai_tracking_db)
    rows = migrated_con.execute(
        "SELECT harness, session_id, list_sort(array_agg(ordinal)) "
        "FROM messages GROUP BY harness, session_id"
    ).fetchall()
    for _harness, _session_id, ordinals in rows:
        assert ordinals == list(range(len(ordinals)))


def test_cursor_enrichment_applied_to_models(
    migrated_con: duckdb.DuckDBPyConnection,
    fixture_roots: None,
    ai_tracking_db: Path,
) -> None:
    """The synthetic ai-code-tracking models land on the matching Cursor session."""
    _full_ingest(migrated_con, ai_tracking_db)
    models = migrated_con.execute(
        "SELECT models FROM sessions "
        "WHERE harness = 'cursor' AND session_id = 'simple-conversation'"
    ).fetchone()[0]
    assert models == ["gpt-5", "claude-4.6-sonnet"]


# --- Workspace identity: project_id (verbatim) + cwd (honest recovery) ------


def test_project_id_is_the_verbatim_slug(
    migrated_con: duckdb.DuckDBPyConnection,
    fixture_roots: None,
    ai_tracking_db: Path,
) -> None:
    """Each session's ``project_id`` is the project dir's verbatim slug — the
    grouping identity, stored exactly as the harness encodes it (Cursor drops
    the leading separator; Claude keeps it as a leading dash).
    """
    _full_ingest(migrated_con, ai_tracking_db)
    cursor_pid = migrated_con.execute(
        "SELECT project_id FROM sessions "
        "WHERE harness = 'cursor' AND session_id = 'simple-conversation'"
    ).fetchone()[0]
    claude_pid = migrated_con.execute(
        "SELECT project_id FROM sessions "
        "WHERE harness = 'claude' AND session_id = '11111111-1111-4111-8111-111111111111'"
    ).fetchone()[0]
    assert cursor_pid == "home-user-project"
    assert claude_pid == "-home-user-project"


def test_cursor_cwd_recovered_from_inband_path(
    migrated_con: duckdb.DuckDBPyConnection,
    fixture_roots: None,
    ai_tracking_db: Path,
) -> None:
    """A Cursor conversation with an in-band absolute path recovers the real
    ``cwd`` by re-encode-and-match — including a hyphenated leaf the naive
    dash->slash decode would have mangled (``/home/user/lite-rpg``, not
    ``/home/user/lite/rpg``).
    """
    _full_ingest(migrated_con, ai_tracking_db)
    cwd = migrated_con.execute(
        "SELECT cwd FROM sessions "
        "WHERE harness = 'cursor' AND session_id = 'recover-inband'"
    ).fetchone()[0]
    assert cwd == "/home/user/lite-rpg"


def test_cursor_cwd_is_null_without_evidence(
    migrated_con: duckdb.DuckDBPyConnection,
    fixture_roots: None,
    ai_tracking_db: Path,
) -> None:
    """A Cursor conversation with no in-band path that re-encodes to its slug
    gets an honest ``cwd = NULL`` (never a fabricated decode).
    """
    _full_ingest(migrated_con, ai_tracking_db)
    cwd = migrated_con.execute(
        "SELECT cwd FROM sessions "
        "WHERE harness = 'cursor' AND session_id = 'ambiguous-nopath'"
    ).fetchone()[0]
    assert cwd is None


def test_no_fabrication_roundtrip_invariant(
    migrated_con: duckdb.DuckDBPyConnection,
    fixture_roots: None,
    ai_tracking_db: Path,
) -> None:
    """Corpus-wide: a populated ``cwd`` always re-encodes back to its own
    ``project_id``. This is the core correctness claim — a fabricated path is
    structurally impossible to store, since the only way ``cwd`` is non-NULL is
    that it matched the slug on the way in (Claude's record cwd round-trips too).
    """
    _full_ingest(migrated_con, ai_tracking_db)
    rows = migrated_con.execute(
        "SELECT harness, project_id, cwd FROM sessions"
    ).fetchall()
    assert rows  # the corpus is non-empty
    for harness, project_id, cwd in rows:
        if cwd is not None:
            assert encode_for(harness, cwd) == project_id


def test_full_ingest_persists_source_mtime_for_sessions_and_subagents(
    migrated_con: duckdb.DuckDBPyConnection,
    fixture_roots: None,
    ai_tracking_db: Path,
) -> None:
    """Each session uses its discovered conversation mtime; subagents inherit it."""
    _full_ingest(migrated_con, ai_tracking_db)
    rows = migrated_con.execute(
        "SELECT harness, session_id, source_path, is_subagent, parent_session_id, "
        "source_mtime FROM sessions ORDER BY harness, session_id"
    ).fetchall()
    assert rows

    by_identity = {
        (harness, session_id): source_mtime
        for harness, session_id, *_, source_mtime in rows
    }
    subagent_count = 0
    for (
        harness,
        _session_id,
        source_path,
        is_subagent,
        parent_id,
        source_mtime,
    ) in rows:
        assert source_mtime is not None
        if is_subagent:
            subagent_count += 1
            assert source_mtime == by_identity[(harness, parent_id)]
        else:
            expected = datetime.fromtimestamp(Path(source_path).stat().st_mtime)
            assert source_mtime == expected
    assert subagent_count > 0


# --- Golden ingest-output snapshot ------------------------------------------


def _jsonable(value: object) -> object:
    """Make a DuckDB cell value JSON-serializable and deterministic."""
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _dump_table(
    con: duckdb.DuckDBPyConnection,
    table: str,
    columns: list[str],
    order_by: str,
    transcripts_dir: Path,
) -> list[dict]:
    rows = con.execute(
        f"SELECT {', '.join(columns)} FROM {table} ORDER BY {order_by}"
    ).fetchall()
    dumped: list[dict] = []
    for row in rows:
        record = {col: _jsonable(val) for col, val in zip(columns, row)}
        if "source_path" in record and record["source_path"] is not None:
            # Relativize the absolute fixture path so the golden is machine-neutral.
            record["source_path"] = (
                Path(record["source_path"])
                .resolve()
                .relative_to(transcripts_dir)
                .as_posix()
            )
        if "tool_input" in record and record["tool_input"] is not None:
            # Parse JSON text so formatting can't perturb the golden.
            record["tool_input"] = json.loads(record["tool_input"])
        dumped.append(record)
    return dumped


def _dump_ingest(con: duckdb.DuckDBPyConnection, transcripts_dir: Path) -> dict:
    """Dump the full reconstruction output (excluding machine-specific watermark)."""
    return {
        "sessions": _dump_table(
            con,
            "sessions",
            [
                "harness",
                "session_id",
                "project_id",
                "cwd",
                "git_branch",
                "source_path",
                "is_subagent",
                "parent_session_id",
                "agent_id",
                "agent_type",
                "spawning_tool_use_id",
                "agent_name",
                "models",
                "title",
                "harness_version",
                "started_at",
                "ended_at",
            ],
            "harness, session_id",
            transcripts_dir,
        ),
        "messages": _dump_table(
            con,
            "messages",
            [
                "harness",
                "session_id",
                "message_id",
                "parent_id",
                "ordinal",
                "role",
                "text",
                "model",
                "ts",
                "input_tokens",
                "output_tokens",
                "cache_creation_tokens",
                "cache_read_tokens",
                "source_uuid",
            ],
            "harness, session_id, ordinal",
            transcripts_dir,
        ),
        "tool_calls": _dump_table(
            con,
            "tool_calls",
            [
                "harness",
                "session_id",
                "message_id",
                "ordinal",
                "tool_name",
                "tool_input",
                "source_tool_use_id",
            ],
            "harness, session_id, message_id, ordinal",
            transcripts_dir,
        ),
    }


def test_ingest_output_matches_golden_snapshot(
    migrated_con: duckdb.DuckDBPyConnection,
    fixture_roots: None,
    ai_tracking_db: Path,
    transcripts_dir: Path,
) -> None:
    """A full fixture ingest byte-matches the committed golden reconstruction.

    This locks every ordinal, parent_id, drop, token value, model, subagent
    edge, and the ``project_id``/``cwd`` of every session. A deliberate parser
    change must regenerate the golden (``STOCKROOM_UPDATE_INGEST_GOLDEN=1``); an
    accidental drift fails here.
    """
    _full_ingest(migrated_con, ai_tracking_db)
    actual = _dump_ingest(migrated_con, transcripts_dir)

    if os.environ.get("STOCKROOM_UPDATE_INGEST_GOLDEN"):
        GOLDEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        GOLDEN_PATH.write_text(
            json.dumps(actual, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    assert GOLDEN_PATH.is_file(), f"golden ingest snapshot missing: {GOLDEN_PATH}"
    expected = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    assert actual == expected
