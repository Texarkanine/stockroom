"""One-shot, opt-in backfill of a harness's legacy store into the warehouse.

Backfill is a deliberate human-run excavation, not part of the nightly path:
nothing under :mod:`stockroom.ingest` or :mod:`stockroom.schedule` imports this
package, and that *absence of an import edge* is the guarantee — asserted by
tests — that ``stockroom ingest`` can never acquire a legacy-store read.

The package mirrors :mod:`stockroom.ingest`'s shape: a harness-neutral
orchestrator over per-source adapter modules. The orchestrator owns the skip
set, the write loop, and the summary; an adapter owns exactly one legacy store
and never issues warehouse SQL. Adding a second harness's store is a new module
beside :mod:`stockroom.backfill.cursor_vscdb`, not orchestrator surgery.

An adapter module satisfies a four-name contract:

``NAME``
    Registry key and ``--source`` value (e.g. ``cursor-vscdb``).
``HARNESS``
    Warehouse ``harness`` label; scopes the skip set and labels the summary.
``resolve_source(override) -> Path``
    Locate the store: explicit override, then env var, then config key. Raises
    :class:`BackfillError` naming all three when none is set.
``candidates(source) -> list[str]``
    Cheaply enumerate the store's session ids, so the orchestrator can subtract
    the skip set *before* paying for the expensive parse.
``parse_all(source, ids) -> Iterator[NormalizedSession]``
    Reconstruct only the requested ids, skipping any that yield no messages.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType

import duckdb

from stockroom import warehouse
from stockroom.ingest import writer

#: Optional progress reporter: one human-readable line per call (CLI wires print).
ProgressCallback = Callable[[str], None]


class BackfillError(RuntimeError):
    """A backfill could not proceed: unresolvable, unreadable, or unknown source.

    Carries an operator-facing one-line remedy; the CLI prints it and exits
    nonzero rather than surfacing a traceback.
    """


@dataclass
class SourceSummary:
    """What one source contributed to a run, and what it deliberately did not.

    The three skip counts are kept apart because they mean different things to
    an operator: ``skipped_existing`` is the safety invariant doing its job,
    ``skipped_empty`` is the source's own dross (empty drafts), and ``skipped``
    with a ``note`` means the source never ran at all. ``error`` is set when a
    configured source could not be read — the run continues, but the CLI exits
    nonzero.
    """

    harness: str = ""
    source_path: str | None = None
    candidates: int = 0
    written: int = 0
    skipped_existing: int = 0
    skipped_empty: int = 0
    messages: int = 0
    tool_calls: int = 0
    note: str | None = None
    error: str | None = None


@dataclass
class BackfillSummary:
    """Per-source outcome for a whole backfill run."""

    by_source: dict[str, SourceSummary] = field(default_factory=dict)

    @property
    def written(self) -> int:
        return sum(source.written for source in self.by_source.values())

    @property
    def failed(self) -> bool:
        """True when any source could not be read (drives a nonzero exit)."""
        return any(source.error is not None for source in self.by_source.values())


def backfill(
    *,
    source: str | None = None,
    source_paths: dict[str, Path] | None = None,
    con: duckdb.DuckDBPyConnection | None = None,
    dry_run: bool = False,
    force: bool = False,
    on_progress: ProgressCallback | None = None,
) -> BackfillSummary:
    """Back-fill every registered source (or just ``source``) into the warehouse.

    For each adapter: resolve its store, enumerate ``candidates`` cheaply,
    subtract the sessions the warehouse already holds for that adapter's
    ``HARNESS``, then parse and write only what remains. ``_sync_state`` is
    never touched — a backfill must not move an ingest watermark.

    ``source_paths`` maps a source ``NAME`` to an explicit store path (the CLI's
    per-adapter override flag). ``dry_run`` parses and counts but writes
    nothing. ``force`` narrows the skip set to sessions *this same source*
    authored, so a corrected parser can replace its own earlier output while
    transcript-authored rows stay untouchable. When ``con`` is ``None`` the
    warehouse is opened read-write — or read-only for a dry run, which needs
    only the skip set and so must not take the single-writer flock.

    Raises :class:`BackfillError` for an unknown ``source`` name, for an
    explicitly named source with no configured store, when no registered
    source is configured at all, and when a dry run finds no usable warehouse
    to compare against. A source that is configured but unreadable is recorded
    on its summary instead, so one broken store cannot hide another's results.
    """
    adapters = _select_adapters(source)
    overrides = source_paths or {}

    resolved: dict[str, Path] = {}
    summary = BackfillSummary()
    for name, adapter in adapters.items():
        try:
            resolved[name] = adapter.resolve_source(overrides.get(name))
        except BackfillError as exc:
            # Naming a source explicitly is a request, not a suggestion: an
            # unconfigured one is an error rather than a silent no-op.
            if source is not None:
                raise
            summary.by_source[name] = SourceSummary(
                harness=adapter.HARNESS, note=str(exc)
            )
    if not resolved:
        raise BackfillError(
            "; ".join(
                source_summary.note or ""
                for source_summary in summary.by_source.values()
            )
        )

    owns_connection = con is None
    connection = con if con is not None else _open_warehouse(dry_run)
    try:
        for name, source_path in resolved.items():
            summary.by_source[name] = _run_source(
                connection,
                adapters[name],
                source_path,
                dry_run=dry_run,
                force=force,
                on_progress=on_progress,
            )
    finally:
        if owns_connection:
            connection.close()
    return summary


def _open_warehouse(dry_run: bool) -> duckdb.DuckDBPyConnection:
    """Open the warehouse for this run: read-write, or read-only for a dry run.

    A dry run only needs the skip set, so it goes through ``open_current`` — the
    read-only door that never migrates. That keeps it off the single-writer
    flock, so rehearsing a backfill cannot queue behind (or delay) a running
    ingest. The tradeoff is that it cannot create a warehouse either, so a
    missing or behind-head one becomes a :class:`BackfillError` naming the
    remedy rather than a side effect nobody asked a *dry* run to perform.
    """
    if not dry_run:
        return warehouse.open(read_only=False)
    try:
        return warehouse.open_current()
    except (FileNotFoundError, warehouse.WarehouseStaleError) as exc:
        raise BackfillError(str(exc)) from exc


def _select_adapters(source: str | None) -> dict[str, ModuleType]:
    """Return the adapters to run: all of them, or just the one named."""
    if source is None:
        return dict(_SOURCES)
    if source not in _SOURCES:
        known = ", ".join(sorted(_SOURCES)) or "(none)"
        raise BackfillError(
            f"unknown backfill source '{source}' — registered sources: {known}"
        )
    return {source: _SOURCES[source]}


def _skip_set(
    con: duckdb.DuckDBPyConnection, harness: str, own_source: str | None
) -> set[str]:
    """Session ids this run must not write, for one adapter's ``harness``.

    By default that is every session the warehouse already holds for the
    harness, because the writer persists by delete-then-insert and would
    otherwise replace a higher-fidelity transcript-authored row with a
    reconstructed one.

    Under ``--force``, ``own_source`` is this adapter's resolved store path and
    rows carrying it are dropped from the skip set — so a corrected parser can
    replace its *own* earlier output without hand-written SQL. Rows any other
    source authored carry a different ``source_path`` and stay protected, which
    is what makes the flag safe to ship rather than a footgun.
    """
    if own_source is None:
        rows = con.execute(
            "SELECT session_id FROM sessions WHERE harness = ?", [harness]
        ).fetchall()
    else:
        rows = con.execute(
            "SELECT session_id FROM sessions "
            "WHERE harness = ? AND source_path IS DISTINCT FROM ?",
            [harness, own_source],
        ).fetchall()
    return {row[0] for row in rows}


def _run_source(
    con: duckdb.DuckDBPyConnection,
    adapter: ModuleType,
    source_path: Path,
    *,
    dry_run: bool,
    force: bool,
    on_progress: ProgressCallback | None,
) -> SourceSummary:
    """Enumerate, skip, parse, and write one source; never raise for a bad store."""
    result = SourceSummary(harness=adapter.HARNESS, source_path=str(source_path))
    try:
        ids = adapter.candidates(source_path)
    except BackfillError as exc:
        result.error = str(exc)
        return result

    result.candidates = len(ids)
    skip = _skip_set(con, adapter.HARNESS, str(source_path) if force else None)
    pending = [candidate for candidate in ids if candidate not in skip]
    result.skipped_existing = result.candidates - len(pending)
    if on_progress is not None:
        on_progress(
            f"{adapter.NAME}: {len(pending)} to reconstruct "
            f"({result.skipped_existing} already in the warehouse)"
        )

    try:
        for session in adapter.parse_all(source_path, pending):
            if not dry_run:
                writer.write_session(con, session)
            result.written += 1
            result.messages += len(session.messages)
            result.tool_calls += sum(
                len(message.tool_calls) for message in session.messages
            )
            if on_progress is not None:
                on_progress(f"{adapter.NAME}: {result.written}/{len(pending)}")
    except BackfillError as exc:
        result.error = str(exc)
        return result

    result.skipped_empty = len(pending) - result.written
    return result


def _builtin_sources() -> dict[str, ModuleType]:
    """Import and register the built-in adapters, keyed by ``NAME``.

    The import is function-local because adapters import :class:`BackfillError`
    from this package: a module-level import here would be circular.
    """
    from stockroom.backfill import cursor_vscdb

    return {module.NAME: module for module in (cursor_vscdb,)}


#: Registered backfill sources: ``NAME`` -> adapter module.
_SOURCES: dict[str, ModuleType] = _builtin_sources()
