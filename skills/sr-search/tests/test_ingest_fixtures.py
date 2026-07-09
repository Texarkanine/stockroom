"""Fixture-integrity tests for the ingest corpus (parser-agnostic).

These tests do not exercise any ingest *code* — they assert that the committed
native-format transcript fixtures and the synthetic enrichment DB exist in the
shape the rest of milestone 3 relies on:

* the two harness roots mirror real on-disk layout (Cursor's
  ``<project>/agent-transcripts/<conv>/<conv>.jsonl`` + ``<conv>/subagents/``;
  Claude's ``<project>/<sessionId>.jsonl`` + ``<sessionId>/subagents/agent-*``),
* every ``.jsonl`` is valid JSON-per-line,
* the trimmed subagent ``meta.json`` carries exactly the real key set,
* the robustness fixture contains the metadata + ignorable record types real
  logs emit (which the m1 fixtures undercounted), and
* the synthetic ``ai-code-tracking.db`` builds with the expected table.

This is the milestone-3 analogue of the m1 fixtures landing as durable,
reviewable artifacts before the code that consumes them exists.
"""

import json
import sqlite3
from pathlib import Path

CURSOR_SESSIONS = [
    "home-user-project/agent-transcripts/simple-conversation/simple-conversation.jsonl",
    "home-user-project/agent-transcripts/pathological-many-tools/pathological-many-tools.jsonl",
    "home-user-project/agent-transcripts/pathological-turn-ended-error/pathological-turn-ended-error.jsonl",
    "home-user-project/agent-transcripts/00000000-0000-4000-8000-000000000001/00000000-0000-4000-8000-000000000001.jsonl",
]

CLAUDE_SESSIONS = [
    "-home-user-project/simple-conversation.jsonl",
    "-home-user-project/pathological-multi-model.jsonl",
    "-home-user-project/pathological-huge-tool-input.jsonl",
    "-home-user-project/robustness-record-types.jsonl",
    "-home-user-project/22222222-2222-4222-8222-222222222222.jsonl",
]


def _read_jsonl(path: Path) -> list[dict]:
    """Parse a JSONL fixture into records, asserting every line is valid JSON."""
    records = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:  # pragma: no cover - failure path
            raise AssertionError(f"{path}:{lineno} is not valid JSON: {exc}") from exc
    return records


def test_harness_roots_exist(cursor_root: Path, claude_root: Path) -> None:
    """Both harness fixture roots are present."""
    assert cursor_root.is_dir()
    assert claude_root.is_dir()


def test_cursor_session_files_present_and_valid(cursor_root: Path) -> None:
    """Each Cursor session file exists, parses, and sits at ``<conv>/<conv>.jsonl``."""
    for rel in CURSOR_SESSIONS:
        path = cursor_root / rel
        assert path.is_file(), f"missing cursor fixture: {path}"
        assert _read_jsonl(path), f"empty cursor fixture: {path}"
        # The conversation file stem equals its parent directory name on disk.
        assert path.stem == path.parent.name


def test_claude_session_files_present_and_valid(claude_root: Path) -> None:
    """Each Claude session file exists and parses as JSON-per-line."""
    for rel in CLAUDE_SESSIONS:
        path = claude_root / rel
        assert path.is_file(), f"missing claude fixture: {path}"
        assert _read_jsonl(path), f"empty claude fixture: {path}"


def test_cursor_subagent_nesting(cursor_root: Path) -> None:
    """The Cursor subagent child lives in ``<conv>/subagents/<child>.jsonl``."""
    conv = cursor_root / (
        "home-user-project/agent-transcripts/00000000-0000-4000-8000-000000000001"
    )
    child = conv / "subagents" / "00000000-0000-4000-8000-0000000000a1.jsonl"
    assert child.is_file()
    assert _read_jsonl(child)


def test_claude_subagent_nesting_and_meta(claude_root: Path) -> None:
    """The Claude subagent sits in ``<session>/subagents/`` with a trimmed meta.

    The ``.meta.json`` carries exactly the real key set
    ``{agentType, description, toolUseId}`` — the m1 fixture's extra
    ``isFork``/``name`` keys were not present in real logs.
    """
    sub = claude_root / (
        "-home-user-project/22222222-2222-4222-8222-222222222222/subagents"
    )
    child = sub / "agent-aaa111.jsonl"
    meta = sub / "agent-aaa111.meta.json"
    assert child.is_file()
    assert meta.is_file()
    meta_obj = json.loads(meta.read_text(encoding="utf-8"))
    assert set(meta_obj) == {"agentType", "description", "toolUseId"}


def test_robustness_fixture_covers_metadata_and_ignorable_types(
    claude_root: Path,
) -> None:
    """The robustness fixture emits the metadata + ignorable record types.

    Real Claude logs interleave many record types the m1 fixtures omitted; the
    Claude parser must fold the metadata records (custom-title, agent-name) and
    ignore the rest without crashing. This fixture is the corpus that proves it.
    """
    path = claude_root / "-home-user-project/robustness-record-types.jsonl"
    types = {r.get("type") for r in _read_jsonl(path)}
    ignorable = {
        "system",
        "attachment",
        "file-history-snapshot",
        "permission-mode",
        "last-prompt",
        "queue-operation",
    }
    assert ignorable <= types, f"missing ignorable types: {ignorable - types}"
    assert {"custom-title", "agent-name"} <= types
    assert {"user", "assistant"} <= types


def test_ai_tracking_db_builds_with_expected_schema(ai_tracking_db: Path) -> None:
    """The synthetic enrichment DB materializes with the current model tables."""
    assert ai_tracking_db.is_file()
    con = sqlite3.connect(ai_tracking_db)
    try:
        tables = {
            r[0]
            for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        assert "ai_code_hashes" in tables
        assert "conversation_summaries" in tables
        count = con.execute("SELECT count(*) FROM ai_code_hashes").fetchone()[0]
        assert count > 0
    finally:
        con.close()
