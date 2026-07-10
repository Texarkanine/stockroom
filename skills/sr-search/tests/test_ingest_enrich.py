"""Tests for the optional Cursor ``ai-code-tracking.db`` enrichment reader.

Enrichment is strictly the model grain ingest consumes (keyed by Cursor
conversation id), which the writer applies to ``sessions.models``. Path
resolution prefers an env override, then searches conventional and WSL
Windows-mount candidates; the reader accepts the current Cursor schema
(``ai_code_hashes``, optionally ``conversation_summaries``) and no-ops when
the DB or tables are absent.
"""

import sqlite3
from pathlib import Path

import pytest

from stockroom.ingest import enrich


def test_absent_db_returns_empty_no_error(tmp_path: Path) -> None:
    """A missing DB file yields empty enrichment rather than raising."""
    assert enrich.read_enrichment(tmp_path / "does-not-exist.db") == {}


def test_none_path_returns_empty(tmp_path: Path) -> None:
    """A ``None`` path (no DB configured) yields empty enrichment."""
    assert enrich.read_enrichment(None) == {}


def test_present_db_returns_models_keyed_by_conversation(ai_tracking_db: Path) -> None:
    """A present DB returns each conversation's distinct models in row order."""
    result = enrich.read_enrichment(ai_tracking_db)
    assert result == {
        "simple-conversation": ["gpt-5", "claude-4.6-sonnet"],
        "00000000-0000-4000-8000-000000000001": ["gpt-5"],
    }


def test_reads_models_from_ai_code_hashes(tmp_path: Path) -> None:
    """Models are read from ``ai_code_hashes`` (current Cursor schema)."""
    db_path = tmp_path / "ai-code-tracking.db"
    con = sqlite3.connect(db_path)
    try:
        con.execute(
            "CREATE TABLE ai_code_hashes ("
            "  hash TEXT PRIMARY KEY,"
            "  conversationId TEXT,"
            "  timestamp INTEGER,"
            "  createdAt INTEGER NOT NULL,"
            "  model TEXT"
            ")"
        )
        con.executemany(
            "INSERT INTO ai_code_hashes "
            "(hash, conversationId, timestamp, createdAt, model) "
            "VALUES (?, ?, ?, ?, ?)",
            [
                ("a", "conv-a", 10, 10, "model-first"),
                ("b", "conv-a", 20, 20, "model-second"),
                ("c", "conv-a", 30, 30, "model-first"),
                ("d", "conv-b", 15, 15, "solo"),
            ],
        )
        con.commit()
    finally:
        con.close()

    assert enrich.read_enrichment(db_path) == {
        "conv-a": ["model-first", "model-second"],
        "conv-b": ["solo"],
    }


def test_merges_conversation_summaries_models(tmp_path: Path) -> None:
    """``conversation_summaries.model`` contributes models not already seen."""
    db_path = tmp_path / "ai-code-tracking.db"
    con = sqlite3.connect(db_path)
    try:
        con.executescript(
            "CREATE TABLE ai_code_hashes ("
            "  hash TEXT PRIMARY KEY,"
            "  conversationId TEXT,"
            "  timestamp INTEGER,"
            "  createdAt INTEGER NOT NULL,"
            "  model TEXT"
            ");"
            "CREATE TABLE conversation_summaries ("
            "  conversationId TEXT PRIMARY KEY,"
            "  model TEXT,"
            "  updatedAt INTEGER NOT NULL"
            ")"
        )
        con.execute(
            "INSERT INTO ai_code_hashes "
            "(hash, conversationId, timestamp, createdAt, model) "
            "VALUES ('h', 'conv-a', 1, 1, 'from-hashes')"
        )
        con.execute(
            "INSERT INTO conversation_summaries "
            "(conversationId, model, updatedAt) "
            "VALUES ('conv-a', 'from-summary', 2)"
        )
        con.execute(
            "INSERT INTO conversation_summaries "
            "(conversationId, model, updatedAt) "
            "VALUES ('conv-b', 'summary-only', 3)"
        )
        con.commit()
    finally:
        con.close()

    assert enrich.read_enrichment(db_path) == {
        "conv-a": ["from-hashes", "from-summary"],
        "conv-b": ["summary-only"],
    }


def test_malformed_db_is_graceful(tmp_path: Path) -> None:
    """A DB without the expected tables no-ops (robust against schema drift)."""
    db_path = tmp_path / "ai-code-tracking.db"
    con = sqlite3.connect(db_path)
    con.execute("CREATE TABLE unrelated (x INTEGER)")
    con.commit()
    con.close()
    assert enrich.read_enrichment(db_path) == {}


def test_default_db_path_env_override(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """``STOCKROOM_AI_TRACKING_DB`` overrides the default DB location."""
    target = tmp_path / "custom" / "ai-code-tracking.db"
    monkeypatch.setenv("STOCKROOM_AI_TRACKING_DB", str(target))
    assert enrich.default_db_path() == target


def test_default_db_path_prefers_ai_tracking_subdir(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Unconfigured resolution prefers ``~/.cursor/ai-tracking/...`` when present."""
    monkeypatch.delenv("STOCKROOM_AI_TRACKING_DB", raising=False)
    home = tmp_path / "home"
    modern = home / ".cursor" / "ai-tracking" / "ai-code-tracking.db"
    legacy = home / ".cursor" / "ai-code-tracking.db"
    modern.parent.mkdir(parents=True, exist_ok=True)
    legacy.parent.mkdir(parents=True, exist_ok=True)
    modern.write_bytes(b"modern")
    legacy.write_bytes(b"legacy")
    monkeypatch.setattr(enrich.Path, "home", staticmethod(lambda: home))
    monkeypatch.setattr(enrich, "_wsl_windows_candidate_paths", lambda: [])
    assert enrich.default_db_path() == modern


def test_default_db_path_falls_back_to_legacy_location(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """When the modern path is missing, the legacy ``~/.cursor/...`` file wins."""
    monkeypatch.delenv("STOCKROOM_AI_TRACKING_DB", raising=False)
    home = tmp_path / "home"
    legacy = home / ".cursor" / "ai-code-tracking.db"
    legacy.parent.mkdir(parents=True)
    legacy.write_bytes(b"legacy")
    monkeypatch.setattr(enrich.Path, "home", staticmethod(lambda: home))
    monkeypatch.setattr(enrich, "_wsl_windows_candidate_paths", lambda: [])
    assert enrich.default_db_path() == legacy


def test_default_db_path_uses_wsl_windows_mount_fallback(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """WSL ``/mnt/<drive>/Users/.../ai-tracking/...`` candidates are searched."""
    monkeypatch.delenv("STOCKROOM_AI_TRACKING_DB", raising=False)
    home = tmp_path / "home"
    home.mkdir()
    wsl_db = tmp_path / "mnt" / "c" / "Users" / "Ada" / ".cursor" / "ai-tracking"
    wsl_db.mkdir(parents=True)
    db_file = wsl_db / "ai-code-tracking.db"
    db_file.write_bytes(b"wsl")
    monkeypatch.setattr(enrich.Path, "home", staticmethod(lambda: home))
    monkeypatch.setattr(enrich, "_wsl_windows_candidate_paths", lambda: [db_file])
    assert enrich.default_db_path() == db_file


def test_default_db_path_returns_modern_conventional_when_absent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """With no candidates on disk, return the documented modern conventional path."""
    monkeypatch.delenv("STOCKROOM_AI_TRACKING_DB", raising=False)
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(enrich.Path, "home", staticmethod(lambda: home))
    monkeypatch.setattr(enrich, "_wsl_windows_candidate_paths", lambda: [])
    assert enrich.default_db_path() == (
        home / ".cursor" / "ai-tracking" / "ai-code-tracking.db"
    )
