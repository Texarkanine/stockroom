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
import shutil
from datetime import datetime
from pathlib import Path

import duckdb
import pytest

from stockroom import ingest
from stockroom.ingest.paths import encode_for

GOLDEN_PATH = Path(__file__).parent / "fixtures" / "ingest" / "expected_rows.json"
CURSOR_CHATS_FIXTURE = (
    Path(__file__).parent
    / "fixtures"
    / "ingest"
    / "cursor_chats"
    / "projhash1234567890abcdefprojhash12"
    / "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    / "store.db"
)


@pytest.fixture
def fixture_roots(
    monkeypatch: pytest.MonkeyPatch,
    cursor_root: Path,
    claude_root: Path,
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """Point the ingest discovery roots at the committed fixtures.

    Chats root defaults to an empty temp dir so the corpus golden stays
    agent-transcripts-only unless a test overrides ``STOCKROOM_CURSOR_CHATS_ROOT``.
    """
    monkeypatch.setenv("STOCKROOM_CURSOR_ROOT", str(cursor_root))
    monkeypatch.setenv("STOCKROOM_CLAUDE_ROOT", str(claude_root))
    empty_chats = tmp_path_factory.mktemp("empty-cursor-chats")
    monkeypatch.setenv("STOCKROOM_CURSOR_CHATS_ROOT", str(empty_chats))


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


def test_ingest_completes_without_progress_callback(
    migrated_con: duckdb.DuckDBPyConnection,
    fixture_roots: None,
    ai_tracking_db: Path,
) -> None:
    """Default ``on_progress=None`` does not require a callback and completes."""
    summary = ingest.ingest(
        full=True, con=migrated_con, harness="claude", ai_tracking_db=ai_tracking_db
    )
    assert summary.by_harness["claude"].sessions > 0


def test_on_progress_reports_harness_start_and_session_counts(
    migrated_con: duckdb.DuckDBPyConnection,
    fixture_roots: None,
    ai_tracking_db: Path,
) -> None:
    """``on_progress`` receives a harness-start line and ``i/N`` lines per selected conversation."""
    lines: list[str] = []
    ingest.ingest(
        full=True,
        con=migrated_con,
        harness="claude",
        ai_tracking_db=ai_tracking_db,
        on_progress=lines.append,
    )
    assert lines, "expected progress lines"
    start = lines[0]
    assert start.startswith("claude: ")
    assert start.endswith(" sessions")
    n = int(start.removeprefix("claude: ").removesuffix(" sessions"))
    assert n > 0
    progress = lines[1:]
    assert len(progress) == n
    for i, line in enumerate(progress, start=1):
        assert line == f"claude: {i}/{n} sessions"


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

    Cursor CLI chats (``entrypoint='cli'``) are exempt: ``project_id`` is the
    chats hash directory, not an ``encode_for`` slug, while ``cwd`` is an honest
    Workspace Path extraction.
    """
    _full_ingest(migrated_con, ai_tracking_db)
    rows = migrated_con.execute(
        "SELECT harness, project_id, cwd, entrypoint FROM sessions"
    ).fetchall()
    assert rows  # the corpus is non-empty
    for harness, project_id, cwd, entrypoint in rows:
        if cwd is not None and entrypoint != "cli":
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
            from stockroom.timestamps import utc_from_timestamp

            expected = utc_from_timestamp(Path(source_path).stat().st_mtime)
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
                "workspace_key",
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
                "entrypoint",
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


def _write_minimal_cursor_transcript(path: Path, *, text: str = "ide turn") -> None:
    """Write a one-user-turn Cursor agent-transcript JSONL at ``path``."""
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "role": "user",
        "message": {"content": [{"type": "text", "text": text}]},
    }
    path.write_text(json.dumps(record) + "\n", encoding="utf-8")


def test_cursor_collision_prefers_store_db_over_transcript(
    migrated_con: duckdb.DuckDBPyConnection,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    ai_tracking_db: Path,
) -> None:
    """Same Cursor ``session_id`` in chats + transcripts → one row from store.db."""
    session_id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    chats_root = tmp_path / "chats"
    projects_root = tmp_path / "projects"
    store_dest = (
        chats_root / "projhash1234567890abcdefprojhash12" / session_id / "store.db"
    )
    store_dest.parent.mkdir(parents=True)
    shutil.copy2(CURSOR_CHATS_FIXTURE, store_dest)
    transcript = (
        projects_root
        / "home-user-project"
        / "agent-transcripts"
        / session_id
        / f"{session_id}.jsonl"
    )
    _write_minimal_cursor_transcript(transcript, text="should not win")

    monkeypatch.setenv("STOCKROOM_CURSOR_CHATS_ROOT", str(chats_root))
    monkeypatch.setenv("STOCKROOM_CURSOR_ROOT", str(projects_root))
    monkeypatch.setenv("STOCKROOM_CLAUDE_ROOT", str(tmp_path / "empty-claude"))
    (tmp_path / "empty-claude").mkdir()

    ingest.ingest(
        full=True, con=migrated_con, harness="cursor", ai_tracking_db=ai_tracking_db
    )
    rows = migrated_con.execute(
        "SELECT session_id, entrypoint, source_path, title FROM sessions "
        "WHERE harness = 'cursor'"
    ).fetchall()
    assert len(rows) == 1
    assert rows[0][0] == session_id
    assert rows[0][1] == "cli"
    assert rows[0][2] == str(store_dest)
    assert rows[0][3] == "Fixture Chat"


def test_cursor_non_collision_keeps_ide_and_cli(
    migrated_con: duckdb.DuckDBPyConnection,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    ai_tracking_db: Path,
) -> None:
    """Distinct ids: transcript-only stays ``ide``; chats-only stays ``cli``."""
    chats_root = tmp_path / "chats"
    projects_root = tmp_path / "projects"
    cli_id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    ide_id = "ffffffff-ffff-ffff-ffff-ffffffffffff"
    store_dest = chats_root / "projhash1234567890abcdefprojhash12" / cli_id / "store.db"
    store_dest.parent.mkdir(parents=True)
    shutil.copy2(CURSOR_CHATS_FIXTURE, store_dest)
    transcript = (
        projects_root
        / "home-user-project"
        / "agent-transcripts"
        / ide_id
        / f"{ide_id}.jsonl"
    )
    _write_minimal_cursor_transcript(transcript, text="ide only")

    monkeypatch.setenv("STOCKROOM_CURSOR_CHATS_ROOT", str(chats_root))
    monkeypatch.setenv("STOCKROOM_CURSOR_ROOT", str(projects_root))
    monkeypatch.setenv("STOCKROOM_CLAUDE_ROOT", str(tmp_path / "empty-claude"))
    (tmp_path / "empty-claude").mkdir()

    ingest.ingest(
        full=True, con=migrated_con, harness="cursor", ai_tracking_db=ai_tracking_db
    )
    by_id = {
        row[0]: row
        for row in migrated_con.execute(
            "SELECT session_id, entrypoint, source_path FROM sessions "
            "WHERE harness = 'cursor'"
        ).fetchall()
    }
    assert set(by_id) == {cli_id, ide_id}
    assert by_id[cli_id][1] == "cli"
    assert by_id[cli_id][2] == str(store_dest)
    assert by_id[ide_id][1] == "ide"
    assert by_id[ide_id][2] == str(transcript)


def test_cursor_chats_watermark_independent_of_projects(
    migrated_con: duckdb.DuckDBPyConnection,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    ai_tracking_db: Path,
) -> None:
    """Chats and projects roots each get their own ``_sync_state`` row."""
    chats_root = tmp_path / "chats"
    projects_root = tmp_path / "projects"
    cli_id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    store_dest = chats_root / "projhash1234567890abcdefprojhash12" / cli_id / "store.db"
    store_dest.parent.mkdir(parents=True)
    shutil.copy2(CURSOR_CHATS_FIXTURE, store_dest)
    ide_id = "ffffffff-ffff-ffff-ffff-ffffffffffff"
    transcript = (
        projects_root
        / "home-user-project"
        / "agent-transcripts"
        / ide_id
        / f"{ide_id}.jsonl"
    )
    _write_minimal_cursor_transcript(transcript)

    monkeypatch.setenv("STOCKROOM_CURSOR_CHATS_ROOT", str(chats_root))
    monkeypatch.setenv("STOCKROOM_CURSOR_ROOT", str(projects_root))
    monkeypatch.setenv("STOCKROOM_CLAUDE_ROOT", str(tmp_path / "empty-claude"))
    (tmp_path / "empty-claude").mkdir()

    ingest.ingest(
        full=True, con=migrated_con, harness="cursor", ai_tracking_db=ai_tracking_db
    )
    roots = {
        row[0]
        for row in migrated_con.execute(
            "SELECT source_root FROM _sync_state WHERE harness = 'cursor'"
        ).fetchall()
    }
    assert roots == {str(chats_root), str(projects_root)}


def test_claude_entrypoint_round_trips_via_ingest(
    migrated_con: duckdb.DuckDBPyConnection,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    ai_tracking_db: Path,
) -> None:
    """Claude JSONL ``entrypoint: claude-desktop`` persists through full ingest."""
    claude_root = tmp_path / "claude"
    session_dir = claude_root / "-tmp-proj"
    session_dir.mkdir(parents=True)
    record = {
        "type": "user",
        "message": {"role": "user", "content": "hello desktop"},
        "uuid": "a1111111-0000-4000-8000-000000000099",
        "parentUuid": None,
        "timestamp": "2026-07-10T03:22:00.000Z",
        "sessionId": "desktop-session",
        "cwd": "/tmp/proj",
        "entrypoint": "claude-desktop",
    }
    (session_dir / "desktop-session.jsonl").write_text(
        json.dumps(record) + "\n", encoding="utf-8"
    )
    monkeypatch.setenv("STOCKROOM_CLAUDE_ROOT", str(claude_root))
    monkeypatch.setenv("STOCKROOM_CURSOR_ROOT", str(tmp_path / "empty-cursor"))
    monkeypatch.setenv("STOCKROOM_CURSOR_CHATS_ROOT", str(tmp_path / "empty-chats"))
    (tmp_path / "empty-cursor").mkdir()
    (tmp_path / "empty-chats").mkdir()

    ingest.ingest(
        full=True, con=migrated_con, harness="claude", ai_tracking_db=ai_tracking_db
    )
    entrypoint = migrated_con.execute(
        "SELECT entrypoint FROM sessions WHERE session_id = 'desktop-session'"
    ).fetchone()[0]
    assert entrypoint == "claude-desktop"


def test_corpus_cursor_sessions_stamp_entrypoint_ide(
    migrated_con: duckdb.DuckDBPyConnection,
    fixture_roots: None,
    ai_tracking_db: Path,
) -> None:
    """Committed agent-transcript corpus sessions synthesize ``entrypoint='ide'``."""
    ingest.ingest(
        full=True, con=migrated_con, harness="cursor", ai_tracking_db=ai_tracking_db
    )
    values = {
        row[0]
        for row in migrated_con.execute(
            "SELECT DISTINCT entrypoint FROM sessions WHERE harness = 'cursor'"
        ).fetchall()
    }
    assert values == {"ide"}
