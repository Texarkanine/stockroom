"""The stockroom trace-ingest (ETL) subsystem.

Fills the milestone-1 DuckDB schema from the operator's own Cursor and Claude
Code history, writing through the milestone-2 ``warehouse.open()`` chokepoint.
The pipeline is, per harness, per run:

    sources (discover + watermark) -> cursor.py / claude.py (clean-room parse
    -> model.NormalizedSession) -> writer (delete-then-insert by
    (harness, session_id)) -> _sync_state watermark update

with an optional ``enrich`` step that folds Cursor ``ai-code-tracking.db``
model/labeling fields in when that DB is present.

:func:`ingest` is the orchestrator entrypoint: it wires discovery -> parse ->
(enrich) -> write -> watermark for each requested harness and returns per-harness
counts. When no connection is injected it opens the warehouse read-write through
the milestone-2 ``warehouse.open()`` chokepoint.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path

import duckdb

from stockroom import warehouse
from stockroom.ingest import claude, cursor, enrich, paths, sources, writer
from stockroom.ingest.model import NormalizedSession

#: The harnesses ingested by default (in deterministic order).
_HARNESSES = ("cursor", "claude")


@dataclass
class HarnessSummary:
    """Counts of rows written for one harness during a run."""

    sessions: int = 0
    messages: int = 0
    tool_calls: int = 0


@dataclass
class IngestSummary:
    """Per-harness write counts for a whole ingest run.

    The aggregate properties sum across harnesses; on a fresh full run they
    equal the warehouse's table row counts.
    """

    by_harness: dict[str, HarnessSummary] = field(default_factory=dict)

    @property
    def sessions(self) -> int:
        return sum(h.sessions for h in self.by_harness.values())

    @property
    def messages(self) -> int:
        return sum(h.messages for h in self.by_harness.values())

    @property
    def tool_calls(self) -> int:
        return sum(h.tool_calls for h in self.by_harness.values())


def _root_for(harness: str) -> Path:
    """The discovery root for a harness (env-resolved)."""
    return sources.cursor_root() if harness == "cursor" else sources.claude_root()


def _read_watermark(
    con: duckdb.DuckDBPyConnection, harness: str, source_root: str
) -> tuple[object, object]:
    """Read the stored ``(last_mtime, last_path)`` watermark, or ``(None, None)``."""
    row = con.execute(
        "SELECT last_mtime, last_path FROM _sync_state "
        "WHERE harness = ? AND source_root = ?",
        [harness, source_root],
    ).fetchone()
    if row is None:
        return None, None
    return row[0], row[1]


def _cursor_texts(session: NormalizedSession) -> list[str]:
    """In-band strings to mine for the real ``cwd`` (message text + tool inputs).

    Cursor transcripts carry no ``cwd`` field, so recovery scans the only
    in-band evidence: each kept turn's text and the serialized JSON of every
    tool input (file paths, cwds, etc.). The serialized form is enough for the
    resolver's absolute-path regex.
    """
    texts: list[str] = []
    for message in session.messages:
        if message.text is not None:
            texts.append(message.text)
        for call in message.tool_calls:
            texts.append(json.dumps(call.tool_input, ensure_ascii=False))
    return texts


def _parse_discovered(
    harness: str,
    discovered: sources.DiscoveredSession,
    enrichment: dict[str, list[str]],
) -> list[NormalizedSession]:
    """Parse one discovered conversation into its session + subagent sessions.

    The parsers leave ``project_id`` unset (it is the verbatim project-dir slug
    from discovery), so the orchestrator stamps it here. ``cwd`` is resolved
    honestly: for Cursor by re-encode-and-match over the conversation's in-band
    paths (``None`` when none re-encodes to the slug); for Claude it is the
    authoritative record ``cwd`` set by the parser (left untouched). Subagents
    inherit the parent's ``project_id`` and ``cwd``. Optional model enrichment is
    applied to the matching Cursor conversation.
    """
    if harness == "cursor":
        main = cursor.parse_session(discovered.session_path)
        main.project_id = discovered.project_id
        main.cwd = paths.resolve_cwd(
            "cursor", discovered.project_id, texts=_cursor_texts(main)
        )
        if main.session_id in enrichment:
            main.models = enrichment[main.session_id]
        result = [main]
        for index, sub_path in enumerate(discovered.subagent_paths):
            sub = cursor.parse_subagent(sub_path, parent=main, index=index)
            sub.project_id = discovered.project_id
            sub.cwd = main.cwd
            result.append(sub)
        return result

    main = claude.parse_session(discovered.session_path)
    main.project_id = discovered.project_id
    result = [main]
    for sub_path in discovered.subagent_paths:
        meta_path = sub_path.with_suffix(".meta.json")
        sub = claude.parse_subagent(sub_path, meta_path=meta_path)
        sub.project_id = discovered.project_id
        result.append(sub)
    return result


def _ingest_harness(
    con: duckdb.DuckDBPyConnection,
    harness: str,
    *,
    full: bool,
    ai_tracking_db: Path | None,
) -> HarnessSummary:
    """Discover, parse, enrich, write, and advance the watermark for one harness."""
    summary = HarnessSummary()
    root = _root_for(harness)
    discovered = sources.discover(harness, root)
    if not discovered:
        return summary
    source_root = str(root)

    if full:
        selected = discovered
    else:
        last_mtime, last_path = _read_watermark(con, harness, source_root)
        selected = sources.select_new(
            discovered, last_mtime=last_mtime, last_path=last_path
        )

    enrichment: dict[str, list[str]] = {}
    if harness == "cursor":
        db_path = (
            ai_tracking_db if ai_tracking_db is not None else enrich.default_db_path()
        )
        enrichment = enrich.read_enrichment(db_path)

    for discovered_session in selected:
        for session in _parse_discovered(harness, discovered_session, enrichment):
            writer.write_session(con, session)
            summary.sessions += 1
            summary.messages += len(session.messages)
            summary.tool_calls += sum(len(m.tool_calls) for m in session.messages)

    # Advance the watermark to the high-water of everything discovered (we have
    # now ingested up to it — the older files were written on prior runs).
    newest = max(discovered, key=lambda d: (d.mtime, d.source_path))
    writer.update_watermark(
        con,
        harness=harness,
        source_root=source_root,
        last_mtime=newest.mtime,
        last_path=newest.source_path,
    )
    return summary


def ingest(
    *,
    harness: str | None = None,
    full: bool = False,
    con: duckdb.DuckDBPyConnection | None = None,
    ai_tracking_db: Path | None = None,
) -> IngestSummary:
    """Run the trace ingest and return per-harness write counts.

    Ingests both harnesses by default, or just ``harness`` when given.
    Incremental by default (only files past the ``_sync_state`` watermark);
    ``full=True`` ignores the watermark and re-ingests everything (idempotent
    via the writer's delete-then-insert). When ``con`` is ``None`` the warehouse
    is opened read-write through ``warehouse.open()`` (and closed on return);
    tests inject a connection. ``ai_tracking_db`` overrides the Cursor
    enrichment DB location (default: :func:`enrich.default_db_path`).
    """
    harnesses = _HARNESSES if harness is None else (harness,)
    summary = IngestSummary()
    owns_connection = con is None
    connection = con if con is not None else warehouse.open(read_only=False)
    try:
        for current in harnesses:
            summary.by_harness[current] = _ingest_harness(
                connection, current, full=full, ai_tracking_db=ai_tracking_db
            )
    finally:
        if owns_connection:
            connection.close()
    return summary
