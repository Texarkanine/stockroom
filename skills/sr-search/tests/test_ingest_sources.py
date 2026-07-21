"""Discovery / path-resolution / watermark tests for ``stockroom.ingest.sources``.

Discovery walks each harness's real on-disk layout under an (env-overridable)
root, enumerating ``(session_file, [subagent_files], project_id, mtime)`` so
the orchestrator can parse and the watermark can skip unchanged files. The
encoded project-dir name is carried *verbatim* as ``project_id`` (no decode —
the real ``cwd`` is recovered downstream). The incremental watermark keeps only
files newer than ``(last_mtime, last_path)``; ``--full`` ignores it.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from stockroom.ingest import sources
from stockroom.timestamps import utc_from_timestamp


def test_root_env_overrides(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The ``STOCKROOM_*_ROOT`` env vars override the default harness roots."""
    monkeypatch.setenv("STOCKROOM_CURSOR_ROOT", str(tmp_path / "cur"))
    monkeypatch.setenv("STOCKROOM_CLAUDE_ROOT", str(tmp_path / "cla"))
    monkeypatch.setenv("STOCKROOM_CURSOR_CHATS_ROOT", str(tmp_path / "chats"))
    assert sources.cursor_root() == tmp_path / "cur"
    assert sources.claude_root() == tmp_path / "cla"
    assert sources.cursor_chats_root() == tmp_path / "chats"


def test_default_roots_when_env_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    """Absent env vars fall back to ``~/.cursor`` and ``~/.claude`` projects."""
    monkeypatch.delenv("STOCKROOM_CURSOR_ROOT", raising=False)
    monkeypatch.delenv("STOCKROOM_CLAUDE_ROOT", raising=False)
    monkeypatch.delenv("STOCKROOM_CURSOR_CHATS_ROOT", raising=False)
    assert sources.cursor_root() == Path.home() / ".cursor" / "projects"
    assert sources.claude_root() == Path.home() / ".claude" / "projects"
    assert sources.cursor_chats_root() == Path.home() / ".cursor" / "chats"


def test_discover_cursor_chats_finds_store_db(tmp_path: Path) -> None:
    """Chats discovery finds ``<hash>/<agentId>/store.db`` with hash as project_id."""
    store = (
        tmp_path
        / "deadbeefcafebabe0123456789abcdef"
        / "11111111-2222-3333-4444-555555555555"
        / "store.db"
    )
    store.parent.mkdir(parents=True)
    store.write_bytes(b"sqlite-placeholder")
    # decoys that must not be discovered
    (tmp_path / "orphan.db").write_bytes(b"x")
    decoy_dir = tmp_path / "hashonly" / "agent-dir"
    decoy_dir.mkdir(parents=True)
    (decoy_dir / "not-a-store.txt").write_text("nope", encoding="utf-8")

    found = sources.discover_cursor_chats(tmp_path)
    assert len(found) == 1
    d = found[0]
    assert d.harness == "cursor"
    assert d.session_path == store
    assert d.project_id == "deadbeefcafebabe0123456789abcdef"
    assert d.subagent_paths == []
    assert d.mtime is not None
    assert d.mtime.tzinfo is None


def test_discover_cursor_chats_sorted_by_path(tmp_path: Path) -> None:
    """Chats discovery returns stores sorted by path for deterministic ingest."""
    stores = []
    for agent in ("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb", "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"):
        p = tmp_path / "hash1" / agent / "store.db"
        p.parent.mkdir(parents=True)
        p.write_bytes(b"x")
        stores.append(p)
    found = sources.discover_cursor_chats(tmp_path)
    assert [d.session_path for d in found] == sorted(stores)


def test_discover_cursor_enumerates_sessions_and_subagents(cursor_root: Path) -> None:
    """Cursor discovery finds every ``<conv>/<conv>.jsonl`` plus its subagents,
    carrying the verbatim project-dir slug and stamping each with its file mtime.
    """
    found = sources.discover("cursor", cursor_root)
    by_stem = {d.session_path.stem: d for d in found}
    # The project-id of each session is the *verbatim* slug of its project dir.
    expected_project_id = {
        "simple-conversation": "home-user-project",
        "pathological-many-tools": "home-user-project",
        "pathological-turn-ended-error": "home-user-project",
        "00000000-0000-4000-8000-000000000001": "home-user-project",
        "recover-inband": "home-user-lite-rpg",
        "ambiguous-nopath": "home-user-cursor-rules",
    }
    assert set(by_stem) == set(expected_project_id)
    for stem, d in by_stem.items():
        assert d.harness == "cursor"
        assert d.project_id == expected_project_id[stem]
        assert isinstance(d.mtime, datetime)
    # Only the subagent-parent conversation has a child transcript.
    parent = by_stem["00000000-0000-4000-8000-000000000001"]
    assert [p.name for p in parent.subagent_paths] == [
        "00000000-0000-4000-8000-0000000000a1.jsonl"
    ]
    assert by_stem["simple-conversation"].subagent_paths == []


def test_discover_claude_enumerates_sessions_and_subagents(claude_root: Path) -> None:
    """Claude discovery finds top-level ``<sessionId>.jsonl`` files (never the
    nested subagent files) and attaches each session's subagent transcripts.
    """
    found = sources.discover("claude", claude_root)
    by_stem = {d.session_path.stem: d for d in found}
    assert set(by_stem) == {
        "simple-conversation",
        "pathological-multi-model",
        "pathological-huge-tool-input",
        "pathological-user-content-shapes",
        "robustness-record-types",
        "22222222-2222-4222-8222-222222222222",
    }
    for d in found:
        assert d.harness == "claude"
        assert d.project_id == "-home-user-project"
    parent = by_stem["22222222-2222-4222-8222-222222222222"]
    assert [p.name for p in parent.subagent_paths] == ["agent-aaa111.jsonl"]


def test_discover_results_are_sorted_deterministically(cursor_root: Path) -> None:
    """Discovery returns sessions in a stable (path-sorted) order."""
    found = sources.discover("cursor", cursor_root)
    paths = [str(d.session_path) for d in found]
    assert paths == sorted(paths)


def _disc(mtime: datetime, path: str) -> sources.DiscoveredSession:
    return sources.DiscoveredSession(
        harness="cursor",
        session_path=Path(path),
        subagent_paths=[],
        project_id=None,
        mtime=mtime,
    )


def test_mtime_is_naive_utc(tmp_path: Path) -> None:
    """Discovered session mtime is naive UTC wall clock, not a non-UTC local wall."""
    conv = tmp_path / "proj" / "agent-transcripts" / "sess"
    conv.mkdir(parents=True)
    path = conv / "sess.jsonl"
    path.write_text("{}\n", encoding="utf-8")

    found = sources.discover("cursor", tmp_path)
    assert len(found) == 1
    got = found[0].mtime
    assert got.tzinfo is None
    assert got == utc_from_timestamp(path.stat().st_mtime)

    eastern = timezone(timedelta(hours=-5))
    local_as_eastern = datetime.fromtimestamp(path.stat().st_mtime, tz=eastern).replace(
        tzinfo=None
    )
    assert got != local_as_eastern


def test_watermark_full_returns_all() -> None:
    """A full run ignores the watermark and returns every discovered session."""
    items = [
        _disc(datetime(2026, 1, 1), "/a.jsonl"),
        _disc(datetime(2026, 1, 2), "/b.jsonl"),
    ]
    assert sources.select_new(items, last_mtime=None, last_path=None) == items


def test_watermark_incremental_filters_by_mtime() -> None:
    """Incremental selection keeps only files strictly newer than the mark."""
    old = _disc(datetime(2026, 1, 1), "/old.jsonl")
    new = _disc(datetime(2026, 1, 3), "/new.jsonl")
    selected = sources.select_new(
        [old, new], last_mtime=datetime(2026, 1, 2), last_path="/x.jsonl"
    )
    assert selected == [new]


def test_watermark_tie_break_on_path() -> None:
    """At an identical mtime, the path breaks the tie (``> last_path``)."""
    same_mtime = datetime(2026, 1, 2)
    lower = _disc(same_mtime, "/a.jsonl")
    higher = _disc(same_mtime, "/z.jsonl")
    selected = sources.select_new(
        [lower, higher], last_mtime=same_mtime, last_path="/a.jsonl"
    )
    assert selected == [higher]
