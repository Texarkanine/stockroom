"""The stockroom trace-ingest (ETL) subsystem.

Fills the DuckDB warehouse from the operator's own Cursor and Claude Code
history, writing through the ``warehouse.open()`` chokepoint.
The pipeline is, per harness, per run:

    sources (discover + watermark) -> cursor.py / cursor_chats.py / claude.py
    (clean-room parse -> model.NormalizedSession) -> writer (delete-then-insert
    by (harness, session_id)) -> _sync_state watermark update

with an optional ``enrich`` step that folds Cursor ``ai-code-tracking.db``
model/labeling fields in when that DB is present. Cursor uses two roots
(projects agent-transcripts + chats ``store.db``); on ``session_id`` collision
the chats store wins.

The warehouse is an append-mostly archive that outlives its sources. A full run
reprocesses only files that still exist; it never prunes orphaned warehouse rows.
The writer carries message observation times through re-ingest, so ``--full`` is
safe for capture-time history as well as source-derived rows.

:func:`ingest` is the orchestrator entrypoint: it wires discovery -> parse ->
(enrich) -> write -> watermark for each requested harness and returns per-harness
counts. When no connection is injected it opens the warehouse read-write through
the milestone-2 ``warehouse.open()`` chokepoint.
"""

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import duckdb

from stockroom import warehouse
from stockroom.ingest import (
    claude,
    cursor,
    cursor_chats,
    enrich,
    paths,
    sources,
    writer,
)
from stockroom.ingest.model import NormalizedSession

#: Optional progress reporter: one human-readable line per call (CLI wires print).
ProgressCallback = Callable[[str], None]

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
    honestly: for Cursor IDE by re-encode-and-match over the conversation's
    in-band paths (``None`` when none re-encodes to the slug); for Cursor CLI
    chats the parser may already set ``cwd`` from Workspace Path (kept when
    present, else resolve_cwd); for Claude it is the authoritative record
    ``cwd`` set by the parser (left untouched). Subagents inherit the parent's
    ``project_id`` and ``cwd``. Every returned session, including subagents,
    inherits the parent conversation's discovered ``source_mtime``. Optional
    model enrichment is applied to the matching Cursor conversation.
    """
    if harness == "cursor":
        if discovered.session_path.name == "store.db":
            main = cursor_chats.parse_session(discovered.session_path)
            main.project_id = discovered.project_id
            if main.cwd is None:
                main.cwd = paths.resolve_cwd(
                    "cursor", discovered.project_id, texts=_cursor_texts(main)
                )
            result = [main]
        else:
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
    else:
        main = claude.parse_session(discovered.session_path)
        main.project_id = discovered.project_id
        result = [main]
        for sub_path in discovered.subagent_paths:
            meta_path = sub_path.with_suffix(".meta.json")
            sub = claude.parse_subagent(sub_path, meta_path=meta_path)
            sub.project_id = discovered.project_id
            result.append(sub)

    for session in result:
        session.source_mtime = discovered.mtime
    return result


def _select_for_root(
    con: duckdb.DuckDBPyConnection,
    harness: str,
    root: Path,
    discovered: list[sources.DiscoveredSession],
    *,
    full: bool,
) -> list[sources.DiscoveredSession]:
    """Apply the ``(harness, source_root)`` watermark unless ``full``."""
    if full:
        return list(discovered)
    last_mtime, last_path = _read_watermark(con, harness, str(root))
    return sources.select_new(discovered, last_mtime=last_mtime, last_path=last_path)


def _advance_watermark(
    con: duckdb.DuckDBPyConnection,
    harness: str,
    root: Path,
    discovered: list[sources.DiscoveredSession],
) -> None:
    """Advance ``_sync_state`` to the high-water of ``discovered`` (if any)."""
    if not discovered:
        return
    newest = max(discovered, key=lambda d: (d.mtime, d.source_path))
    writer.update_watermark(
        con,
        harness=harness,
        source_root=str(root),
        last_mtime=newest.mtime,
        last_path=newest.source_path,
    )


def _write_discovered(
    con: duckdb.DuckDBPyConnection,
    harness: str,
    selected: list[sources.DiscoveredSession],
    enrichment: dict[str, list[str]],
    summary: HarnessSummary,
    *,
    on_progress: ProgressCallback | None,
    progress_offset: int,
    progress_total: int,
) -> int:
    """Parse+write each selected discovery; return how many were processed."""
    for index, discovered_session in enumerate(selected, start=1):
        for session in _parse_discovered(harness, discovered_session, enrichment):
            writer.write_session(con, session)
            summary.sessions += 1
            summary.messages += len(session.messages)
            summary.tool_calls += sum(len(m.tool_calls) for m in session.messages)
        if on_progress is not None:
            on_progress(
                f"{harness}: {progress_offset + index}/{progress_total} sessions"
            )
    return len(selected)


def _ingest_cursor(
    con: duckdb.DuckDBPyConnection,
    *,
    full: bool,
    ai_tracking_db: Path | None,
    on_progress: ProgressCallback | None = None,
) -> HarnessSummary:
    """Ingest Cursor from chats (``store.db``) and agent-transcripts.

    Chats are authoritative on ``session_id`` collision: discover chats first,
    build the id set, then filter transcript discoveries. Each root keeps its
    own ``_sync_state`` watermark under ``harness='cursor'``.
    """
    summary = HarnessSummary()
    chats_root = sources.cursor_chats_root()
    projects_root = sources.cursor_root()

    chats_discovered = sources.discover_cursor_chats(chats_root)
    chat_ids = {d.session_path.parent.name for d in chats_discovered}

    transcripts_discovered = [
        d
        for d in sources.discover("cursor", projects_root)
        if d.session_path.stem not in chat_ids
    ]

    chats_selected = _select_for_root(
        con, "cursor", chats_root, chats_discovered, full=full
    )
    transcripts_selected = _select_for_root(
        con, "cursor", projects_root, transcripts_discovered, full=full
    )
    selected = [*chats_selected, *transcripts_selected]
    if not chats_discovered and not transcripts_discovered:
        return summary

    total = len(selected)
    if on_progress is not None:
        on_progress(f"cursor: {total} sessions")

    db_path = ai_tracking_db if ai_tracking_db is not None else enrich.default_db_path()
    enrichment = enrich.read_enrichment(db_path)

    offset = _write_discovered(
        con,
        "cursor",
        chats_selected,
        enrichment,
        summary,
        on_progress=on_progress,
        progress_offset=0,
        progress_total=total,
    )
    _write_discovered(
        con,
        "cursor",
        transcripts_selected,
        enrichment,
        summary,
        on_progress=on_progress,
        progress_offset=offset,
        progress_total=total,
    )

    _advance_watermark(con, "cursor", chats_root, chats_discovered)
    _advance_watermark(con, "cursor", projects_root, transcripts_discovered)
    return summary


def _ingest_harness(
    con: duckdb.DuckDBPyConnection,
    harness: str,
    *,
    full: bool,
    ai_tracking_db: Path | None,
    on_progress: ProgressCallback | None = None,
) -> HarnessSummary:
    """Discover, parse, enrich, write, and advance the watermark for one harness.

    When ``on_progress`` is set, emits a harness-start line with the selected
    conversation count, then ``{harness}: i/N sessions`` after each selected
    conversation is processed (``N`` is selected discovered conversations, not
    subagent-inflated write counts).
    """
    if harness == "cursor":
        return _ingest_cursor(
            con,
            full=full,
            ai_tracking_db=ai_tracking_db,
            on_progress=on_progress,
        )

    summary = HarnessSummary()
    root = _root_for(harness)
    discovered = sources.discover(harness, root)
    if not discovered:
        return summary

    selected = _select_for_root(con, harness, root, discovered, full=full)

    total = len(selected)
    if on_progress is not None:
        on_progress(f"{harness}: {total} sessions")

    _write_discovered(
        con,
        harness,
        selected,
        {},
        summary,
        on_progress=on_progress,
        progress_offset=0,
        progress_total=total,
    )
    _advance_watermark(con, harness, root, discovered)
    return summary


def ingest(
    *,
    harness: str | None = None,
    full: bool = False,
    con: duckdb.DuckDBPyConnection | None = None,
    ai_tracking_db: Path | None = None,
    on_progress: ProgressCallback | None = None,
) -> IngestSummary:
    """Run the trace ingest and return per-harness write counts.

    Ingests both harnesses by default, or just ``harness`` when given.
    Incremental by default (only files past the ``_sync_state`` watermark);
    ``full=True`` ignores the watermark and re-ingests everything (idempotent
    via the writer's delete-then-insert). When ``con`` is ``None`` the warehouse
    is opened read-write through ``warehouse.open()`` (and closed on return);
    tests inject a connection. ``ai_tracking_db`` overrides the Cursor
    enrichment DB location (default: :func:`enrich.default_db_path`).
    ``on_progress``, when set, receives human-readable progress lines (see
    :func:`_ingest_harness`); default ``None`` emits nothing.
    """
    harnesses = _HARNESSES if harness is None else (harness,)
    summary = IngestSummary()
    owns_connection = con is None
    connection = con if con is not None else warehouse.open(read_only=False)
    try:
        for current in harnesses:
            summary.by_harness[current] = _ingest_harness(
                connection,
                current,
                full=full,
                ai_tracking_db=ai_tracking_db,
                on_progress=on_progress,
            )
    finally:
        if owns_connection:
            connection.close()
    return summary
