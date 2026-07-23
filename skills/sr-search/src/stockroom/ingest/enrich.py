"""Optional model enrichment from Cursor's ``ai-code-tracking.db``.

Cursor records have no per-message model and no session-grain model set, so the
``sessions.models`` grain for Cursor is filled (when available) from this
sidecar sqlite DB. The reader is strictly limited to the model grain ingest
consumes — Cursor's attribution tables are out of scope.

The DB is **optional**: every entry point degrades to an empty result rather
than raising, so ingest runs identically with or without it. Path resolution
walks **all** readable conventional candidates (Linux modern/legacy + WSL
Windows-home mounts) and merges them with optional XDG
``[cursor].ai_tracking_dbs`` pins. ``STOCKROOM_AI_TRACKING_DB`` forces a
single-DB override (tests / one-shots). The present-DB path reads the current
Cursor schema (``ai_code_hashes``, optionally ``conversation_summaries``)
through stdlib :mod:`sqlite3` only — no new dependency.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from stockroom import config

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


def _normalize_db_path(path: Path) -> Path:
    """Expand ``~``; resolve when the path exists (best-effort dedupe key)."""
    expanded = Path(path).expanduser()
    try:
        if expanded.exists():
            return expanded.resolve()
    except OSError:
        pass
    return expanded


def resolve_db_paths() -> list[Path]:
    """Return enrichment DB paths to read (env override, else discovery ∪ pins).

    When ``STOCKROOM_AI_TRACKING_DB`` is set, returns that single path.
    Otherwise returns every existing conventional candidate plus every
    configured ``ai_tracking_dbs`` pin (deduped, discovery order then pins).
    Missing pins remain in the list so :func:`read_enrichment` can fail soft.
    """
    override = os.environ.get(AI_TRACKING_DB_ENV_VAR)
    if override:
        return [Path(override)]

    ordered: list[Path] = []
    seen: set[Path] = set()

    def _add(path: Path, *, require_file: bool) -> None:
        normalized = _normalize_db_path(path)
        if require_file and not normalized.is_file():
            return
        if normalized in seen:
            return
        seen.add(normalized)
        ordered.append(normalized)

    for candidate in _candidate_db_paths():
        _add(candidate, require_file=True)
    for pin in config.load_settings().cursor_ai_tracking_dbs:
        _add(pin, require_file=False)
    return ordered


def load_enrichment() -> dict[str, list[str]]:
    """Resolve all enrichment DB paths and merge their model maps fail-soft.

    Walks :func:`resolve_db_paths`, reads each with :func:`read_enrichment`,
    and merges ``{conversation_id: [model, ...]}`` with first-seen model order
    via :func:`_append_model`. Unreadable / missing paths contribute nothing.
    """
    merged: dict[str, list[str]] = {}
    for db_path in resolve_db_paths():
        for conversation_id, models in read_enrichment(db_path).items():
            for model in models:
                _append_model(merged, conversation_id, model)
    return merged


def default_db_path() -> Path:
    """Return a single enrichment DB path for diagnostics / thin callers.

    Prefers the first path from :func:`resolve_db_paths` (including the
    ``STOCKROOM_AI_TRACKING_DB`` singleton), else the documented modern
    conventional path under ``~/.cursor/ai-tracking/``. Prefer
    :func:`load_enrichment` for ingest.
    """
    resolved = resolve_db_paths()
    if resolved:
        return resolved[0]
    return _candidate_db_paths()[0]


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
