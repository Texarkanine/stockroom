"""Tests for the optional Cursor ``ai-code-tracking.db`` enrichment reader.

Enrichment is strictly the model grain ingest consumes (keyed by Cursor
conversation id), which the writer applies to ``sessions.models``. Path
resolution walks all readable conventional/WSL candidates and merges with
optional XDG ``ai_tracking_dbs`` pins; ``STOCKROOM_AI_TRACKING_DB`` forces a
single DB. The reader accepts the current Cursor schema (``ai_code_hashes``,
optionally ``conversation_summaries``) and no-ops when the DB or tables are
absent.
"""

import sqlite3
from pathlib import Path

import pytest

from stockroom import config
from stockroom.ingest import enrich


def _write_tracking_db(path: Path, rows: list[tuple[str, str, str, int]]) -> Path:
    """Create a minimal ``ai_code_hashes`` DB at ``path``.

    Each row is ``(hash, conversation_id, model, timestamp)``.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
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
            [(h, cid, ts, ts, model) for h, cid, model, ts in rows],
        )
        con.commit()
    finally:
        con.close()
    return path


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


def test_resolve_db_paths_env_override_is_singleton(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """``STOCKROOM_AI_TRACKING_DB`` forces a single path (walk disabled)."""
    target = tmp_path / "custom" / "ai-code-tracking.db"
    home_dir = tmp_path / "home"
    modern = home_dir / ".cursor" / "ai-tracking" / "ai-code-tracking.db"
    modern.parent.mkdir(parents=True)
    modern.write_bytes(b"shadow")
    monkeypatch.setenv("STOCKROOM_AI_TRACKING_DB", str(target))
    monkeypatch.setattr(enrich.Path, "home", staticmethod(lambda: home_dir))
    monkeypatch.setattr(enrich, "_wsl_windows_candidate_paths", lambda: [])
    assert enrich.resolve_db_paths() == [target]


def test_resolve_db_paths_walks_home_and_wsl_candidates(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Both home modern and WSL candidates are returned when both exist."""
    monkeypatch.delenv("STOCKROOM_AI_TRACKING_DB", raising=False)
    home_dir = tmp_path / "home"
    modern = home_dir / ".cursor" / "ai-tracking" / "ai-code-tracking.db"
    modern.parent.mkdir(parents=True)
    modern.write_bytes(b"cli")
    wsl = tmp_path / "mnt" / "c" / "Users" / "Ada" / ".cursor" / "ai-tracking"
    wsl.mkdir(parents=True)
    wsl_db = wsl / "ai-code-tracking.db"
    wsl_db.write_bytes(b"ide")
    monkeypatch.setattr(enrich.Path, "home", staticmethod(lambda: home_dir))
    monkeypatch.setattr(enrich, "_wsl_windows_candidate_paths", lambda: [wsl_db])
    monkeypatch.setattr(
        config, "load_settings", lambda config_home=None: config.Settings()
    )
    assert enrich.resolve_db_paths() == [modern.resolve(), wsl_db.resolve()]


def test_resolve_db_paths_includes_legacy_when_modern_absent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Legacy ``~/.cursor/ai-code-tracking.db`` is discovered when modern is missing."""
    monkeypatch.delenv("STOCKROOM_AI_TRACKING_DB", raising=False)
    home_dir = tmp_path / "home"
    legacy = home_dir / ".cursor" / "ai-code-tracking.db"
    legacy.parent.mkdir(parents=True)
    legacy.write_bytes(b"legacy")
    monkeypatch.setattr(enrich.Path, "home", staticmethod(lambda: home_dir))
    monkeypatch.setattr(enrich, "_wsl_windows_candidate_paths", lambda: [])
    monkeypatch.setattr(
        config, "load_settings", lambda config_home=None: config.Settings()
    )
    assert enrich.resolve_db_paths() == [legacy.resolve()]


def test_resolve_db_paths_config_pins_additive(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """XDG ``ai_tracking_dbs`` pins are unioned with discovery (not a replace)."""
    monkeypatch.delenv("STOCKROOM_AI_TRACKING_DB", raising=False)
    home_dir = tmp_path / "home"
    modern = home_dir / ".cursor" / "ai-tracking" / "ai-code-tracking.db"
    modern.parent.mkdir(parents=True)
    modern.write_bytes(b"cli")
    pin = tmp_path / "odd-mount" / "ai-code-tracking.db"
    pin.parent.mkdir(parents=True)
    pin.write_bytes(b"pin")
    monkeypatch.setattr(enrich.Path, "home", staticmethod(lambda: home_dir))
    monkeypatch.setattr(enrich, "_wsl_windows_candidate_paths", lambda: [])
    monkeypatch.setattr(
        config,
        "load_settings",
        lambda config_home=None: config.Settings(cursor_ai_tracking_dbs=(pin,)),
    )
    assert enrich.resolve_db_paths() == [modern.resolve(), pin.resolve()]


def test_resolve_db_paths_dedupes_pin_already_discovered(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A pin that matches a discovered path appears once."""
    monkeypatch.delenv("STOCKROOM_AI_TRACKING_DB", raising=False)
    home_dir = tmp_path / "home"
    modern = home_dir / ".cursor" / "ai-tracking" / "ai-code-tracking.db"
    modern.parent.mkdir(parents=True)
    modern.write_bytes(b"cli")
    monkeypatch.setattr(enrich.Path, "home", staticmethod(lambda: home_dir))
    monkeypatch.setattr(enrich, "_wsl_windows_candidate_paths", lambda: [])
    monkeypatch.setattr(
        config,
        "load_settings",
        lambda config_home=None: config.Settings(cursor_ai_tracking_dbs=(modern,)),
    )
    assert enrich.resolve_db_paths() == [modern.resolve()]


def test_resolve_db_paths_keeps_missing_config_pin(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Missing pin paths stay in the resolve set (fail-soft on read)."""
    monkeypatch.delenv("STOCKROOM_AI_TRACKING_DB", raising=False)
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    missing = tmp_path / "gone" / "ai-code-tracking.db"
    monkeypatch.setattr(enrich.Path, "home", staticmethod(lambda: home_dir))
    monkeypatch.setattr(enrich, "_wsl_windows_candidate_paths", lambda: [])
    monkeypatch.setattr(
        config,
        "load_settings",
        lambda config_home=None: config.Settings(cursor_ai_tracking_dbs=(missing,)),
    )
    assert enrich.resolve_db_paths() == [missing]


def test_resolve_db_paths_empty_when_nothing_found(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """No files and no pins → empty resolve list."""
    monkeypatch.delenv("STOCKROOM_AI_TRACKING_DB", raising=False)
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    monkeypatch.setattr(enrich.Path, "home", staticmethod(lambda: home_dir))
    monkeypatch.setattr(enrich, "_wsl_windows_candidate_paths", lambda: [])
    monkeypatch.setattr(
        config, "load_settings", lambda config_home=None: config.Settings()
    )
    assert enrich.resolve_db_paths() == []


def test_default_db_path_env_override(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """``STOCKROOM_AI_TRACKING_DB`` still drives the thin single-path helper."""
    target = tmp_path / "custom" / "ai-code-tracking.db"
    monkeypatch.setenv("STOCKROOM_AI_TRACKING_DB", str(target))
    assert enrich.default_db_path() == target


def test_default_db_path_returns_modern_conventional_when_absent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """With no candidates on disk, return the documented modern conventional path."""
    monkeypatch.delenv("STOCKROOM_AI_TRACKING_DB", raising=False)
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    monkeypatch.setattr(enrich.Path, "home", staticmethod(lambda: home_dir))
    monkeypatch.setattr(enrich, "_wsl_windows_candidate_paths", lambda: [])
    monkeypatch.setattr(
        config, "load_settings", lambda config_home=None: config.Settings()
    )
    assert enrich.default_db_path() == (
        home_dir / ".cursor" / "ai-tracking" / "ai-code-tracking.db"
    )


def test_load_enrichment_merges_disjoint_conversation_ids(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Two DBs with disjoint conversationIds contribute both model maps."""
    cli = _write_tracking_db(
        tmp_path / "cli.db",
        [("h1", "cli-conv", "model-cli", 1)],
    )
    ide = _write_tracking_db(
        tmp_path / "ide.db",
        [("h2", "ide-conv", "model-ide", 2)],
    )
    monkeypatch.setattr(enrich, "resolve_db_paths", lambda: [cli, ide])
    assert enrich.load_enrichment() == {
        "cli-conv": ["model-cli"],
        "ide-conv": ["model-ide"],
    }


def test_load_enrichment_shadowing_regression(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Home (first) DB must not hide IDE models from a later candidate."""
    home_db = _write_tracking_db(
        tmp_path / "home.db",
        [("h1", "cli-only", "gpt-cli", 1)],
    )
    ide_db = _write_tracking_db(
        tmp_path / "ide.db",
        [("h2", "ide-only", "gpt-ide", 2)],
    )
    monkeypatch.setattr(enrich, "resolve_db_paths", lambda: [home_db, ide_db])
    result = enrich.load_enrichment()
    assert result["cli-only"] == ["gpt-cli"]
    assert result["ide-only"] == ["gpt-ide"]


def test_load_enrichment_skips_unreadable_sibling(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A missing/unreadable path does not drop models from readable siblings."""
    good = _write_tracking_db(
        tmp_path / "good.db",
        [("h1", "conv-a", "model-a", 1)],
    )
    missing = tmp_path / "missing.db"
    monkeypatch.setattr(enrich, "resolve_db_paths", lambda: [missing, good])
    assert enrich.load_enrichment() == {"conv-a": ["model-a"]}


def test_load_enrichment_dedupes_models_across_dbs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Same conversationId + model across DBs keeps first-seen order only."""
    first = _write_tracking_db(
        tmp_path / "a.db",
        [("h1", "shared", "model-x", 1), ("h2", "shared", "model-y", 2)],
    )
    second = _write_tracking_db(
        tmp_path / "b.db",
        [("h3", "shared", "model-x", 3), ("h4", "shared", "model-z", 4)],
    )
    monkeypatch.setattr(enrich, "resolve_db_paths", lambda: [first, second])
    assert enrich.load_enrichment() == {"shared": ["model-x", "model-y", "model-z"]}


def test_load_enrichment_empty_when_no_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No resolved paths → empty enrichment map."""
    monkeypatch.setattr(enrich, "resolve_db_paths", lambda: [])
    assert enrich.load_enrichment() == {}
