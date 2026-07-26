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

from types import ModuleType


class BackfillError(RuntimeError):
    """A backfill could not proceed: unresolvable, unreadable, or unknown source.

    Carries an operator-facing one-line remedy; the CLI prints it and exits
    nonzero rather than surfacing a traceback.
    """


def _builtin_sources() -> dict[str, ModuleType]:
    """Import and register the built-in adapters, keyed by ``NAME``.

    The import is function-local because adapters import :class:`BackfillError`
    from this package: a module-level import here would be circular.
    """
    from stockroom.backfill import cursor_vscdb

    return {module.NAME: module for module in (cursor_vscdb,)}


#: Registered backfill sources: ``NAME`` -> adapter module.
_SOURCES: dict[str, ModuleType] = _builtin_sources()
