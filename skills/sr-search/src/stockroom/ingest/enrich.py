"""Optional model enrichment from Cursor's ``ai-code-tracking.db``.

Cursor records have no per-message model and no session-grain model set, so the
``sessions.models`` grain for Cursor is filled (when available) from this
sidecar sqlite DB. The reader is strictly limited to the model grain ingest
consumes — Cursor's attribution tables are out of scope for milestone 3.

The DB is **optional and frequently absent** (it is absent on the operator's
current machine): every entry point degrades to an empty result rather than
raising, so ingest runs identically with or without it. The present-DB path is
clean-room (reconstructed from the model-usage shape, operator-vetted Cursor
provenance) and reads through stdlib :mod:`sqlite3` only — no new dependency.
"""

import os
import sqlite3
from pathlib import Path

#: Env var overriding where the Cursor ``ai-code-tracking.db`` is read from.
AI_TRACKING_DB_ENV_VAR = "STOCKROOM_AI_TRACKING_DB"

#: Conventional default location (best-effort; absence is a graceful no-op).
_DEFAULT_DB = Path.home() / ".cursor" / "ai-code-tracking.db"


def default_db_path() -> Path:
    """Return the enrichment DB path (env override or the conventional default).

    The path is not required to exist — :func:`read_enrichment` treats a missing
    file as "no enrichment available".
    """
    override = os.environ.get(AI_TRACKING_DB_ENV_VAR)
    return Path(override) if override else _DEFAULT_DB


def read_enrichment(db_path: Path | None) -> dict[str, list[str]]:
    """Read per-conversation model enrichment, keyed by Cursor conversation id.

    Returns ``{conversation_id: [model, ...]}`` with each conversation's models
    de-duplicated in first-seen row order. Returns an empty mapping — never
    raising — when ``db_path`` is ``None``, the file is absent, or the DB lacks
    the expected ``conversation_model_usage`` table (robust against schema
    drift on machines where the DB exists but differs).
    """
    if db_path is None:
        return {}
    db_path = Path(db_path)
    if not db_path.is_file():
        return {}

    enrichment: dict[str, list[str]] = {}
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        try:
            rows = con.execute(
                "SELECT conversation_id, model FROM conversation_model_usage"
            ).fetchall()
        except sqlite3.Error:
            return {}
    finally:
        con.close()

    for conversation_id, model in rows:
        if conversation_id is None or model is None:
            continue
        models = enrichment.setdefault(conversation_id, [])
        if model not in models:
            models.append(model)
    return enrichment
