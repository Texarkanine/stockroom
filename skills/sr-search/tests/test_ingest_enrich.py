"""Tests for the optional Cursor ``ai-code-tracking.db`` enrichment reader.

The DB is *absent* on the operator's current machine, so the no-op path is a
first-class tested behavior; the present-DB path is exercised against the
synthetic ``ai_tracking_db`` fixture. Enrichment is strictly the model grain
ingest consumes (keyed by Cursor conversation id), which the writer applies to
``sessions.models``.
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


def test_malformed_db_is_graceful(tmp_path: Path) -> None:
    """A DB without the expected table no-ops (robust against schema drift)."""
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
