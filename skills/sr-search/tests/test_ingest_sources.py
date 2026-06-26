"""Discovery / path-resolution / watermark tests for ``stockroom.ingest.sources``.

Discovery walks each harness's real on-disk layout under an (env-overridable)
root, enumerating ``(session_file, [subagent_files], project_path, mtime)`` so
the orchestrator can parse and the watermark can skip unchanged files. The
encoded project-dir name decodes (lossily) to a plausible absolute path. The
incremental watermark keeps only files newer than ``(last_mtime, last_path)``;
``--full`` ignores it.
"""

from datetime import datetime
from pathlib import Path

import pytest

from stockroom.ingest import sources


def test_root_env_overrides(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The ``STOCKROOM_*_ROOT`` env vars override the default harness roots."""
    monkeypatch.setenv("STOCKROOM_CURSOR_ROOT", str(tmp_path / "cur"))
    monkeypatch.setenv("STOCKROOM_CLAUDE_ROOT", str(tmp_path / "cla"))
    assert sources.cursor_root() == tmp_path / "cur"
    assert sources.claude_root() == tmp_path / "cla"


def test_default_roots_when_env_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    """Absent env vars fall back to ``~/.cursor`` and ``~/.claude`` projects."""
    monkeypatch.delenv("STOCKROOM_CURSOR_ROOT", raising=False)
    monkeypatch.delenv("STOCKROOM_CLAUDE_ROOT", raising=False)
    assert sources.cursor_root() == Path.home() / ".cursor" / "projects"
    assert sources.claude_root() == Path.home() / ".claude" / "projects"


def test_decode_project_dir() -> None:
    """Encoded project-dir names decode to plausible absolute paths.

    Cursor drops the leading slash in its encoding; Claude keeps it as a leading
    dash. Both map interior dashes to slashes (lossy, best-effort).
    """
    assert sources.decode_project_dir("home-user-project") == "/home/user/project"
    assert sources.decode_project_dir("-home-user-project") == "/home/user/project"
    assert (
        sources.decode_project_dir("-mnt-v-users-Austin-git-app")
        == "/mnt/v/users/Austin/git/app"
    )


def test_discover_cursor_enumerates_sessions_and_subagents(cursor_root: Path) -> None:
    """Cursor discovery finds every ``<conv>/<conv>.jsonl`` plus its subagents,
    decoding the project path and stamping each with its file mtime.
    """
    found = sources.discover("cursor", cursor_root)
    by_stem = {d.session_path.stem: d for d in found}
    assert set(by_stem) == {
        "simple-conversation",
        "pathological-many-tools",
        "pathological-turn-ended-error",
        "00000000-0000-4000-8000-000000000001",
    }
    for d in found:
        assert d.harness == "cursor"
        assert d.project_path == "/home/user/project"
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
        assert d.project_path == "/home/user/project"
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
        project_path=None,
        mtime=mtime,
    )


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
