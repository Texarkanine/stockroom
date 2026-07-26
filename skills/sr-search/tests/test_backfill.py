"""Orchestrator and registry tests for ``stockroom.backfill``.

Backfill writes to the same warehouse ordinary ingest owns, so these tests
mostly pin what it must *not* do: never clobber a session another source
authored, never move a ``_sync_state`` watermark, never appear on the nightly
path. The registry conformance case is parametrized over ``_SOURCES``, so a
future adapter is checked the day it lands.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable, Iterator
from pathlib import Path
from types import SimpleNamespace

import duckdb
import pytest

from stockroom import backfill as backfill_pkg
from stockroom import ingest, schedule
from stockroom.backfill import BackfillError, cursor_vscdb
from stockroom.ingest.model import NormalizedMessage, NormalizedSession

TOOL_BUBBLE = {
    "type": 2,
    "text": "editing",
    "toolFormerData": {
        "name": "edit_file",
        "toolCallId": "call_1",
        "rawArgs": '{"path": "/home/u/p/a.py"}',
        "result": '{"output": "SECRET"}',
    },
}


def _one_composer_db(build_vscdb: Callable[..., Path], **kwargs) -> Path:
    """A store holding a single two-message composer ``c1`` in workspace ``w1``."""
    defaults = {
        "composers": {"c1": {"fullConversationHeadersOnly": _headers("b1", "b2")}},
        "bubbles": {"c1:b1": {"type": 1, "text": "ask"}, "c1:b2": TOOL_BUBBLE},
        "headers": {"c1": "w1"},
        "workspaces": {"w1": {"folder": "vscode-remote://wsl%2Bubuntu/home/u/p"}},
    }
    defaults.update(kwargs)
    return build_vscdb(**defaults)


def _headers(*bubble_ids: str) -> list[dict]:
    """A ``fullConversationHeadersOnly`` list alternating user/assistant."""
    return [
        {"bubbleId": bubble_id, "type": 1 if index % 2 == 0 else 2}
        for index, bubble_id in enumerate(bubble_ids)
    ]


@pytest.fixture
def only_cursor_vscdb(monkeypatch: pytest.MonkeyPatch) -> None:
    """Register exactly the real adapter, isolated from future registrations."""
    monkeypatch.setattr(
        backfill_pkg, "_SOURCES", {cursor_vscdb.NAME: cursor_vscdb}, raising=True
    )


def _stub_adapter(
    name: str,
    *,
    harness: str = "stub",
    sessions: list[NormalizedSession] | None = None,
    source: Path | None = None,
    calls: list[str] | None = None,
) -> SimpleNamespace:
    """Build an in-memory adapter satisfying the four-name contract.

    Records every contract call into ``calls`` so a test can assert ordering,
    and accepts no warehouse connection anywhere — which is the point.
    """
    sessions = sessions or []
    log = calls if calls is not None else []

    def resolve_source(override: Path | None = None) -> Path:
        log.append(f"{name}:resolve")
        if override is not None:
            return override
        if source is None:
            raise BackfillError(f"{name}: nothing configured")
        return source

    def candidates(resolved: Path) -> list[str]:
        log.append(f"{name}:candidates")
        return [session.session_id for session in sessions]

    def parse_all(resolved: Path, ids: list[str]) -> Iterator[NormalizedSession]:
        log.append(f"{name}:parse_all:{','.join(ids)}")
        for session in sessions:
            if session.session_id in ids:
                yield session

    return SimpleNamespace(
        NAME=name,
        HARNESS=harness,
        resolve_source=resolve_source,
        candidates=candidates,
        parse_all=parse_all,
    )


def _stub_session(session_id: str, harness: str = "stub") -> NormalizedSession:
    """A minimal one-message session a stub adapter can emit."""
    return NormalizedSession(
        harness=harness,
        session_id=session_id,
        source_path="/stub/store",
        messages=[NormalizedMessage(ordinal=0, role="user", text="hi")],
    )


def _count(con: duckdb.DuckDBPyConnection, table: str) -> int:
    return con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]


def _dump(con: duckdb.DuckDBPyConnection, table: str) -> list[tuple]:
    """Every row of ``table`` in a stable order, for before/after comparison."""
    return con.execute(f"SELECT * FROM {table} ORDER BY ALL").fetchall()


# --- source registry (D3) ----------------------------------------------------


@pytest.mark.parametrize("registry_key", sorted(backfill_pkg._SOURCES))
def test_every_registered_source_satisfies_the_adapter_contract(
    registry_key: str,
) -> None:
    """Each adapter exposes NAME/HARNESS plus the three callables, keyed by NAME."""
    adapter = backfill_pkg._SOURCES[registry_key]
    assert adapter.NAME == registry_key
    assert isinstance(adapter.HARNESS, str) and adapter.HARNESS
    for contract_name in ("resolve_source", "candidates", "parse_all"):
        assert callable(getattr(adapter, contract_name)), contract_name


def test_orchestrator_subtracts_the_skip_set_before_parsing(
    migrated_con: duckdb.DuckDBPyConnection, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``candidates`` runs first so existing ids never reach the costly parse."""
    calls: list[str] = []
    adapter = _stub_adapter(
        "stub",
        sessions=[_stub_session("keep"), _stub_session("already-there")],
        source=Path("/stub/store"),
        calls=calls,
    )
    monkeypatch.setattr(backfill_pkg, "_SOURCES", {"stub": adapter})
    from stockroom.ingest import writer

    writer.write_session(migrated_con, _stub_session("already-there"))

    backfill_pkg.backfill(con=migrated_con)
    assert calls == ["stub:resolve", "stub:candidates", "stub:parse_all:keep"]


def test_skip_set_is_scoped_to_the_adapter_harness(
    migrated_con: duckdb.DuckDBPyConnection, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Another harness's session with the same id does not mask a candidate."""
    from stockroom.ingest import writer

    writer.write_session(migrated_con, _stub_session("shared-id", harness="claude"))
    adapter = _stub_adapter(
        "stub", sessions=[_stub_session("shared-id")], source=Path("/stub/store")
    )
    monkeypatch.setattr(backfill_pkg, "_SOURCES", {"stub": adapter})

    summary = backfill_pkg.backfill(con=migrated_con)
    assert summary.by_source["stub"].written == 1
    assert _count(migrated_con, "sessions") == 2


def test_named_source_runs_only_that_source(
    migrated_con: duckdb.DuckDBPyConnection, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``source=NAME`` runs one adapter and leaves the others untouched."""
    calls: list[str] = []
    first = _stub_adapter(
        "one", sessions=[_stub_session("s1")], source=Path("/a"), calls=calls
    )
    second = _stub_adapter(
        "two", sessions=[_stub_session("s2")], source=Path("/b"), calls=calls
    )
    monkeypatch.setattr(backfill_pkg, "_SOURCES", {"one": first, "two": second})

    summary = backfill_pkg.backfill(con=migrated_con, source="two")
    assert set(summary.by_source) == {"two"}
    assert not any(call.startswith("one:") for call in calls)


def test_unknown_source_name_errors_listing_the_registered_ones(
    migrated_con: duckdb.DuckDBPyConnection, only_cursor_vscdb: None
) -> None:
    """An unknown ``--source`` value names what is actually registered."""
    with pytest.raises(BackfillError) as excinfo:
        backfill_pkg.backfill(con=migrated_con, source="claude-legacy")
    message = str(excinfo.value)
    assert "claude-legacy" in message
    assert cursor_vscdb.NAME in message


def test_unconfigured_source_is_reported_and_skipped_when_others_run(
    migrated_con: duckdb.DuckDBPyConnection, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Multi-source tolerance: one unconfigured source does not fail the run."""
    configured = _stub_adapter("one", sessions=[_stub_session("s1")], source=Path("/a"))
    unconfigured = _stub_adapter("two", source=None)
    monkeypatch.setattr(
        backfill_pkg, "_SOURCES", {"one": configured, "two": unconfigured}
    )

    summary = backfill_pkg.backfill(con=migrated_con)
    assert summary.by_source["one"].written == 1
    assert summary.by_source["two"].written == 0
    assert summary.by_source["two"].note is not None
    assert not summary.failed


def test_explicitly_named_unconfigured_source_is_an_error(
    migrated_con: duckdb.DuckDBPyConnection, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Asking for a source by name and getting nothing configured is an error."""
    configured = _stub_adapter("one", sessions=[], source=Path("/a"))
    unconfigured = _stub_adapter("two", source=None)
    monkeypatch.setattr(
        backfill_pkg, "_SOURCES", {"one": configured, "two": unconfigured}
    )

    with pytest.raises(BackfillError):
        backfill_pkg.backfill(con=migrated_con, source="two")


def test_all_sources_unconfigured_is_an_error(
    migrated_con: duckdb.DuckDBPyConnection, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A run that could not have done anything reports it rather than succeeding."""
    monkeypatch.setattr(
        backfill_pkg,
        "_SOURCES",
        {"one": _stub_adapter("one"), "two": _stub_adapter("two")},
    )
    with pytest.raises(BackfillError):
        backfill_pkg.backfill(con=migrated_con)


def test_adapters_are_never_handed_a_warehouse_connection(
    migrated_con: duckdb.DuckDBPyConnection, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The orchestrator is the only warehouse SQL touchpoint; adapters get none.

    The stub's contract functions accept no connection parameter at all, so a
    successful write proves the orchestrator kept the warehouse to itself.
    """
    adapter = _stub_adapter(
        "stub", sessions=[_stub_session("s1")], source=Path("/stub/store")
    )
    monkeypatch.setattr(backfill_pkg, "_SOURCES", {"stub": adapter})
    for contract_name in ("candidates", "parse_all", "resolve_source"):
        parameters = inspect.signature(getattr(adapter, contract_name)).parameters
        assert "con" not in parameters, contract_name

    backfill_pkg.backfill(con=migrated_con)
    assert _count(migrated_con, "sessions") == 1


# --- run behavior ------------------------------------------------------------


def test_absent_composers_are_written_to_the_warehouse(
    migrated_con: duckdb.DuckDBPyConnection,
    build_vscdb: Callable[..., Path],
    only_cursor_vscdb: None,
) -> None:
    """A composer missing from the warehouse lands as sessions/messages/tool_calls."""
    db_path = _one_composer_db(build_vscdb)
    summary = backfill_pkg.backfill(
        con=migrated_con, source_paths={cursor_vscdb.NAME: db_path}
    )

    assert summary.by_source[cursor_vscdb.NAME].written == 1
    assert _count(migrated_con, "sessions") == 1
    assert _count(migrated_con, "messages") == 2
    assert _count(migrated_con, "tool_calls") == 1
    row = migrated_con.execute(
        "SELECT harness, entrypoint, source_path, project_id, cwd FROM sessions"
    ).fetchone()
    assert row == ("cursor", "ide", str(db_path), "w1", "/home/u/p")


def test_existing_session_is_skipped_and_left_byte_identical(
    migrated_con: duckdb.DuckDBPyConnection,
    build_vscdb: Callable[..., Path],
    only_cursor_vscdb: None,
) -> None:
    """The writer deletes by (harness, session_id): a bad skip set would clobber."""
    from stockroom.ingest import writer

    incumbent = NormalizedSession(
        harness="cursor",
        session_id="c1",
        source_path="/home/u/.cursor/projects/p/agent-transcripts/c1/c1.jsonl",
        title="authored by ingest",
        messages=[NormalizedMessage(ordinal=0, role="user", text="original")],
    )
    writer.write_session(migrated_con, incumbent)
    before_sessions = _dump(migrated_con, "sessions")
    before_messages = _dump(migrated_con, "messages")

    db_path = _one_composer_db(build_vscdb)
    summary = backfill_pkg.backfill(
        con=migrated_con, source_paths={cursor_vscdb.NAME: db_path}
    )

    assert summary.by_source[cursor_vscdb.NAME].skipped_existing == 1
    assert summary.by_source[cursor_vscdb.NAME].written == 0
    assert _dump(migrated_con, "sessions") == before_sessions
    assert _dump(migrated_con, "messages") == before_messages


def test_run_does_not_touch_sync_state_watermarks(
    migrated_con: duckdb.DuckDBPyConnection,
    build_vscdb: Callable[..., Path],
    only_cursor_vscdb: None,
) -> None:
    """Backfill must never advance (or create) an ingest watermark."""
    from datetime import datetime

    from stockroom.ingest import writer

    writer.update_watermark(
        migrated_con,
        harness="cursor",
        source_root="/home/u/.cursor/projects",
        last_mtime=datetime(2026, 1, 1),
        last_path="/home/u/.cursor/projects/p/agent-transcripts/x/x.jsonl",
    )
    before = _dump(migrated_con, "_sync_state")

    backfill_pkg.backfill(
        con=migrated_con,
        source_paths={cursor_vscdb.NAME: _one_composer_db(build_vscdb)},
    )
    assert _dump(migrated_con, "_sync_state") == before


def test_running_twice_is_idempotent(
    migrated_con: duckdb.DuckDBPyConnection,
    build_vscdb: Callable[..., Path],
    only_cursor_vscdb: None,
) -> None:
    """A second run writes nothing new and reports everything as already present."""
    db_path = _one_composer_db(build_vscdb)
    paths = {cursor_vscdb.NAME: db_path}
    backfill_pkg.backfill(con=migrated_con, source_paths=paths)
    after_first = {
        table: _dump(migrated_con, table)
        for table in ("sessions", "messages", "tool_calls")
    }

    second = backfill_pkg.backfill(con=migrated_con, source_paths=paths)
    assert second.by_source[cursor_vscdb.NAME].written == 0
    assert second.by_source[cursor_vscdb.NAME].skipped_existing == 1
    for table, rows in after_first.items():
        assert _dump(migrated_con, table) == rows, table


def test_summary_reports_per_source_counts(
    migrated_con: duckdb.DuckDBPyConnection,
    build_vscdb: Callable[..., Path],
    only_cursor_vscdb: None,
) -> None:
    """Candidates / written / skipped-existing / skipped-empty plus row counts."""
    db_path = build_vscdb(
        composers={
            "c1": {"fullConversationHeadersOnly": _headers("b1", "b2")},
            "empty-draft": {"name": "never sent"},
        },
        bubbles={"c1:b1": {"type": 1, "text": "ask"}, "c1:b2": TOOL_BUBBLE},
    )
    summary = backfill_pkg.backfill(
        con=migrated_con, source_paths={cursor_vscdb.NAME: db_path}
    )

    source = summary.by_source[cursor_vscdb.NAME]
    assert source.harness == "cursor"
    assert source.source_path == str(db_path)
    assert source.candidates == 2
    assert source.written == 1
    assert source.skipped_existing == 0
    assert source.skipped_empty == 1
    assert source.messages == 2
    assert source.tool_calls == 1


def test_dry_run_writes_nothing_but_reports_what_it_would_write(
    migrated_con: duckdb.DuckDBPyConnection,
    build_vscdb: Callable[..., Path],
    only_cursor_vscdb: None,
) -> None:
    """``--dry-run`` is the undo-shaped safety net the pre-mortem asked for."""
    summary = backfill_pkg.backfill(
        con=migrated_con,
        source_paths={cursor_vscdb.NAME: _one_composer_db(build_vscdb)},
        dry_run=True,
    )
    assert summary.by_source[cursor_vscdb.NAME].written == 1
    assert summary.by_source[cursor_vscdb.NAME].messages == 2
    assert _count(migrated_con, "sessions") == 0
    assert _count(migrated_con, "messages") == 0


def test_dry_run_does_not_create_or_migrate_a_missing_warehouse(
    warehouse_home: Path,
    build_vscdb: Callable[..., Path],
    only_cursor_vscdb: None,
) -> None:
    """A dry run opens the warehouse read-only, so it cannot conjure one.

    Behavioral proof that the dry-run path is not ``open(read_only=False)``:
    that door creates the file, migrates it, and takes the single-writer flock.
    A dry run must do none of those, so with no warehouse on disk it has to
    refuse — with the remedy named, and nothing left behind.
    """
    with pytest.raises(backfill_pkg.BackfillError) as excinfo:
        backfill_pkg.backfill(
            source_paths={cursor_vscdb.NAME: _one_composer_db(build_vscdb)},
            dry_run=True,
        )
    assert "stockroom ingest" in str(excinfo.value)
    assert not (warehouse_home / "warehouse.duckdb").exists()


def test_unreadable_source_is_reported_without_a_traceback(
    migrated_con: duckdb.DuckDBPyConnection, tmp_path: Path, only_cursor_vscdb: None
) -> None:
    """A configured but unreadable store yields a typed error, not a crash."""
    missing = tmp_path / "nowhere" / "state.vscdb"
    summary = backfill_pkg.backfill(
        con=migrated_con, source_paths={cursor_vscdb.NAME: missing}
    )
    assert summary.failed
    assert str(missing) in summary.by_source[cursor_vscdb.NAME].error


def test_unconfigured_real_source_error_names_flag_env_and_config(
    migrated_con: duckdb.DuckDBPyConnection,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    only_cursor_vscdb: None,
) -> None:
    """With nothing configured, the message names all three ways to configure it."""
    monkeypatch.delenv(cursor_vscdb.STATE_VSCDB_ENV_VAR, raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "empty-xdg"))
    with pytest.raises(BackfillError) as excinfo:
        backfill_pkg.backfill(con=migrated_con)
    message = str(excinfo.value)
    assert cursor_vscdb.STATE_VSCDB_FLAG in message
    assert cursor_vscdb.STATE_VSCDB_ENV_VAR in message
    assert cursor_vscdb.STATE_VSCDB_CONFIG_KEY in message


# --- the --force re-parse escape hatch (D7) ----------------------------------


def _retext_bubble(db_path: Path, key: str, text: str) -> None:
    """Rewrite one bubble's text in place, standing in for a corrected parse."""
    import json
    import sqlite3

    con = sqlite3.connect(db_path)
    try:
        con.execute(
            "UPDATE cursorDiskKV SET value = ? WHERE key = ?",
            (json.dumps({"type": 1, "text": text}), key),
        )
        con.commit()
    finally:
        con.close()


def test_force_reparses_a_session_this_source_authored(
    migrated_con: duckdb.DuckDBPyConnection,
    build_vscdb: Callable[..., Path],
    only_cursor_vscdb: None,
) -> None:
    """A parser fix must be applicable without hand-written DELETE against the
    shared warehouse — but only to rows this same store authored."""
    db_path = _one_composer_db(build_vscdb)
    paths = {cursor_vscdb.NAME: db_path}
    backfill_pkg.backfill(con=migrated_con, source_paths=paths)
    _retext_bubble(db_path, "bubbleId:c1:b1", "corrected reconstruction")

    summary = backfill_pkg.backfill(con=migrated_con, source_paths=paths, force=True)

    assert summary.by_source[cursor_vscdb.NAME].written == 1
    assert summary.by_source[cursor_vscdb.NAME].skipped_existing == 0
    text = migrated_con.execute(
        "SELECT text FROM messages WHERE message_id = 'c1#0'"
    ).fetchone()[0]
    assert text == "corrected reconstruction"


def test_force_still_skips_a_session_ordinary_ingest_authored(
    migrated_con: duckdb.DuckDBPyConnection,
    build_vscdb: Callable[..., Path],
    only_cursor_vscdb: None,
) -> None:
    """Constraint 2 holds even under force: a transcript-authored row is safe."""
    from stockroom.ingest import writer

    writer.write_session(
        migrated_con,
        NormalizedSession(
            harness="cursor",
            session_id="c1",
            source_path="/home/u/.cursor/projects/p/agent-transcripts/c1/c1.jsonl",
            messages=[NormalizedMessage(ordinal=0, role="user", text="from ingest")],
        ),
    )
    before_sessions = _dump(migrated_con, "sessions")
    before_messages = _dump(migrated_con, "messages")

    summary = backfill_pkg.backfill(
        con=migrated_con,
        source_paths={cursor_vscdb.NAME: _one_composer_db(build_vscdb)},
        force=True,
    )

    assert summary.by_source[cursor_vscdb.NAME].written == 0
    assert summary.by_source[cursor_vscdb.NAME].skipped_existing == 1
    assert _dump(migrated_con, "sessions") == before_sessions
    assert _dump(migrated_con, "messages") == before_messages


def test_without_force_a_previously_backfilled_session_is_skipped(
    migrated_con: duckdb.DuckDBPyConnection,
    build_vscdb: Callable[..., Path],
    only_cursor_vscdb: None,
) -> None:
    """The default is unchanged: own rows are skipped like any other."""
    db_path = _one_composer_db(build_vscdb)
    paths = {cursor_vscdb.NAME: db_path}
    backfill_pkg.backfill(con=migrated_con, source_paths=paths)
    _retext_bubble(db_path, "bubbleId:c1:b1", "corrected reconstruction")

    summary = backfill_pkg.backfill(con=migrated_con, source_paths=paths)

    assert summary.by_source[cursor_vscdb.NAME].written == 0
    text = migrated_con.execute(
        "SELECT text FROM messages WHERE message_id = 'c1#0'"
    ).fetchone()[0]
    assert text == "ask"


# --- guard tests (encode the invariants) -------------------------------------


def test_nightly_schedule_payload_never_mentions_backfill(tmp_path: Path) -> None:
    """Constraint 1: the scheduled entry stays ``ingest && embed``."""
    assert "backfill" not in schedule.render_payload(tmp_path)


def test_ingest_package_has_no_import_edge_to_backfill() -> None:
    """The absence of this edge *is* the "not nightly" guarantee.

    The check is on the *import path* rather than the bare word, so it catches
    a static import and an ``importlib.import_module`` alike while still
    letting ingest prose name backfill as the motivating case for shared
    behaviour (the writer's ``first_seen_at`` fallback does exactly that).
    """
    ingest_dir = Path(ingest.__file__).parent
    offenders = [
        module.name
        for module in sorted(ingest_dir.glob("*.py"))
        if "stockroom.backfill" in module.read_text(encoding="utf-8")
    ]
    assert offenders == []


# --- integration -------------------------------------------------------------


def test_backfilled_session_converges_with_a_same_cwd_ingest_session(
    migrated_con: duckdb.DuckDBPyConnection,
    build_vscdb: Callable[..., Path],
    only_cursor_vscdb: None,
) -> None:
    """OQ2's claim: the writer-derived ``workspace_key`` matches across sources."""
    from stockroom.ingest import writer

    writer.write_session(
        migrated_con,
        NormalizedSession(
            harness="cursor",
            session_id="transcript-session",
            source_path="/home/u/.cursor/projects/home-u-p/agent-transcripts/t/t.jsonl",
            project_id="home-u-p",
            cwd="/home/u/p",
            messages=[NormalizedMessage(ordinal=0, role="user", text="hi")],
        ),
    )
    backfill_pkg.backfill(
        con=migrated_con,
        source_paths={cursor_vscdb.NAME: _one_composer_db(build_vscdb)},
    )

    keys = migrated_con.execute(
        "SELECT session_id, project_id, workspace_key FROM sessions ORDER BY session_id"
    ).fetchall()
    assert [row[0] for row in keys] == ["c1", "transcript-session"]
    # Different project_id namespaces, one shared rollup key.
    assert keys[0][1] != keys[1][1]
    assert keys[0][2] == keys[1][2] is not None


def test_message_ids_expand_from_positional_identity(
    migrated_con: duckdb.DuckDBPyConnection,
    build_vscdb: Callable[..., Path],
    only_cursor_vscdb: None,
) -> None:
    """Backfilled rows use the same ``{session_id}#{ordinal}`` identity as ingest."""
    backfill_pkg.backfill(
        con=migrated_con,
        source_paths={cursor_vscdb.NAME: _one_composer_db(build_vscdb)},
    )
    rows = migrated_con.execute(
        "SELECT message_id, parent_id FROM messages ORDER BY ordinal"
    ).fetchall()
    assert rows == [("c1#0", None), ("c1#1", "c1#0")]
    assert migrated_con.execute("SELECT message_id FROM tool_calls").fetchone() == (
        "c1#1",
    )


def test_token_grain_rolls_up_as_message_through_the_view(
    migrated_con: duckdb.DuckDBPyConnection,
    build_vscdb: Callable[..., Path],
    only_cursor_vscdb: None,
) -> None:
    """D6: ``session_token_usage`` reports ``message`` grain, native totals NULL."""
    db_path = build_vscdb(
        composers={"c1": {"fullConversationHeadersOnly": _headers("b1", "b2")}},
        bubbles={
            "c1:b1": {"type": 1, "text": "ask"},
            "c1:b2": {
                "type": 2,
                "text": "answer",
                "tokenCount": {"inputTokens": 6078, "outputTokens": 512},
            },
        },
    )
    backfill_pkg.backfill(con=migrated_con, source_paths={cursor_vscdb.NAME: db_path})

    row = migrated_con.execute(
        "SELECT token_grain, input_tokens_native, output_tokens_native, "
        "input_tokens_total, output_tokens_total, input_tokens_from_messages "
        "FROM session_token_usage WHERE session_id = 'c1'"
    ).fetchone()
    assert row == ("message", None, None, 6078, 512, 6078)


def test_tokenless_backfilled_session_reports_no_token_grain(
    migrated_con: duckdb.DuckDBPyConnection,
    build_vscdb: Callable[..., Path],
    only_cursor_vscdb: None,
) -> None:
    """A composer Cursor never metered honestly reports ``none``."""
    backfill_pkg.backfill(
        con=migrated_con,
        source_paths={cursor_vscdb.NAME: _one_composer_db(build_vscdb)},
    )
    grain = migrated_con.execute(
        "SELECT token_grain FROM session_token_usage WHERE session_id = 'c1'"
    ).fetchone()[0]
    assert grain == "none"


def test_backfill_leaves_ingest_authored_rows_and_watermarks_untouched(
    migrated_con: duckdb.DuckDBPyConnection,
    build_vscdb: Callable[..., Path],
    only_cursor_vscdb: None,
    monkeypatch: pytest.MonkeyPatch,
    cursor_root: Path,
    claude_root: Path,
    ai_tracking_db: Path,
    tmp_path: Path,
) -> None:
    """Run ordinary ingest, then backfill: nothing ingest wrote may change."""
    monkeypatch.setenv("STOCKROOM_CURSOR_ROOT", str(cursor_root))
    monkeypatch.setenv("STOCKROOM_CLAUDE_ROOT", str(claude_root))
    empty_chats = tmp_path / "empty-cursor-chats"
    empty_chats.mkdir()
    monkeypatch.setenv("STOCKROOM_CURSOR_CHATS_ROOT", str(empty_chats))

    ingest.ingest(full=True, con=migrated_con, ai_tracking_db=ai_tracking_db)
    before = {
        table: _dump(migrated_con, table)
        for table in ("sessions", "messages", "tool_calls", "_sync_state")
    }

    summary = backfill_pkg.backfill(
        con=migrated_con,
        source_paths={cursor_vscdb.NAME: _one_composer_db(build_vscdb)},
    )
    assert summary.by_source[cursor_vscdb.NAME].written == 1

    assert _dump(migrated_con, "_sync_state") == before["_sync_state"]
    for table in ("sessions", "messages", "tool_calls"):
        preserved = [row for row in _dump(migrated_con, table) if row in before[table]]
        assert preserved == before[table], table


def test_tool_results_never_reach_the_warehouse(
    migrated_con: duckdb.DuckDBPyConnection,
    build_vscdb: Callable[..., Path],
    only_cursor_vscdb: None,
) -> None:
    """Invariant 8 end to end: tool inputs are stored whole, results never."""
    backfill_pkg.backfill(
        con=migrated_con,
        source_paths={cursor_vscdb.NAME: _one_composer_db(build_vscdb)},
    )
    tool_input = migrated_con.execute("SELECT tool_input FROM tool_calls").fetchone()[0]
    assert "/home/u/p/a.py" in tool_input
    assert "SECRET" not in tool_input
