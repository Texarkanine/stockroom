"""Optional model enrichment from Cursor's ``ai-code-tracking.db``.

Cursor records have no per-message model and no session-grain model set, so the
``sessions.models`` grain for Cursor is filled (when available) from this
sidecar sqlite DB. The reader is strictly limited to the model grain ingest
consumes — Cursor's attribution tables are out of scope.

The DB is **optional**: every entry point degrades to an empty result rather
than raising, so ingest runs identically with or without it. Path resolution
prefers ``STOCKROOM_AI_TRACKING_DB``, then conventional locations under
``~/.cursor/``, then WSL Windows-home mount fallbacks. The present-DB path
reads the current Cursor schema (``ai_code_hashes``, optionally
``conversation_summaries``) through stdlib :mod:`sqlite3` only — no new
dependency.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

#: Env var overriding where the Cursor ``ai-code-tracking.db`` is read from.
AI_TRACKING_DB_ENV_VAR = "STOCKROOM_AI_TRACKING_DB"

#: Relative path under a ``.cursor`` directory for the current layout.
_MODERN_REL = Path("ai-tracking") / "ai-code-tracking.db"

#: Relative path under a ``.cursor`` directory for the legacy layout.
_LEGACY_REL = Path("ai-code-tracking.db")


def _wsl_windows_candidate_paths() -> list[Path]:
    """Return candidate DB paths under WSL ``/mnt/<drive>/Users/*/.cursor/...``.

    Searches both the modern ``ai-tracking/`` layout and the legacy flat path.
    Missing mounts or permission errors yield an empty list — never raise.
    """
    mnt = Path("/mnt")
    if not mnt.is_dir():
        return []

    candidates: list[Path] = []
    try:
        drives = sorted(p for p in mnt.iterdir() if p.is_dir())
    except OSError:
        return []

    for drive in drives:
        users_root = drive / "Users"
        if not users_root.is_dir():
            continue
        try:
            user_homes = sorted(p for p in users_root.iterdir() if p.is_dir())
        except OSError:
            continue
        for user_home in user_homes:
            cursor_dir = user_home / ".cursor"
            candidates.append(cursor_dir / _MODERN_REL)
            candidates.append(cursor_dir / _LEGACY_REL)
    return candidates


def _candidate_db_paths(home: Path | None = None) -> list[Path]:
    """Ordered candidate enrichment DB paths (excluding the env override)."""
    home = Path.home() if home is None else home
    cursor_dir = home / ".cursor"
    return [
        cursor_dir / _MODERN_REL,
        cursor_dir / _LEGACY_REL,
        *_wsl_windows_candidate_paths(),
    ]


def default_db_path() -> Path:
    """Return the enrichment DB path (env override or first existing candidate).

    When nothing exists on disk, returns the documented modern conventional
    path under ``~/.cursor/ai-tracking/``. The path is not required to exist —
    :func:`read_enrichment` treats a missing file as "no enrichment available".
    """
    override = os.environ.get(AI_TRACKING_DB_ENV_VAR)
    if override:
        return Path(override)

    candidates = _candidate_db_paths()
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return candidates[0]


def _append_model(
    enrichment: dict[str, list[str]], conversation_id: object, model: object
) -> None:
    """Append ``model`` to ``conversation_id``'s list if both are non-null and new."""
    if conversation_id is None or model is None:
        return
    conversation_key = str(conversation_id)
    model_name = str(model)
    if not conversation_key or not model_name:
        return
    models = enrichment.setdefault(conversation_key, [])
    if model_name not in models:
        models.append(model_name)


def _table_exists(con: sqlite3.Connection, table: str) -> bool:
    row = con.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table,),
    ).fetchone()
    return row is not None


def read_enrichment(db_path: Path | None) -> dict[str, list[str]]:
    """Read per-conversation model enrichment, keyed by Cursor conversation id.

    Returns ``{conversation_id: [model, ...]}`` with each conversation's models
    de-duplicated in first-seen order. Prefer rows from ``ai_code_hashes``
    (ordered by ``timestamp``, then ``createdAt``), then any additional models
    from ``conversation_summaries``. Returns an empty mapping — never raising —
    when ``db_path`` is ``None``, the file is absent, or neither expected table
    is present (robust against schema drift).
    """
    if db_path is None:
        return {}
    db_path = Path(db_path)
    if not db_path.is_file():
        return {}

    enrichment: dict[str, list[str]] = {}
    try:
        con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    except sqlite3.Error:
        return {}

    try:
        try:
            if _table_exists(con, "ai_code_hashes"):
                rows = con.execute(
                    "SELECT conversationId, model FROM ai_code_hashes "
                    "ORDER BY timestamp ASC NULLS LAST, "
                    "createdAt ASC NULLS LAST, rowid ASC"
                ).fetchall()
                for conversation_id, model in rows:
                    _append_model(enrichment, conversation_id, model)

            if _table_exists(con, "conversation_summaries"):
                rows = con.execute(
                    "SELECT conversationId, model FROM conversation_summaries "
                    "ORDER BY updatedAt ASC NULLS LAST, rowid ASC"
                ).fetchall()
                for conversation_id, model in rows:
                    _append_model(enrichment, conversation_id, model)
        except sqlite3.Error:
            return {}
    finally:
        con.close()

    return enrichment
