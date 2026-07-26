# Backfill Adapters

`stockroom backfill` is an orchestrator over a registry of per-source adapters, mirroring how ingest is an orchestrator over per-harness parsers. Teaching it to read another harness's legacy store is a new module plus a registry entry — not orchestrator surgery.

Read [Architecture → Backfill](../../architecture/backfill.md) first if you have not; it owns the *why* (why this is off the nightly path, why the orchestrator holds all the SQL, why provenance is exact). This page is the loop.

## Layout

Paths below are relative to `skills/sr-search/`.

| Path | Role |
| --- | --- |
| `src/stockroom/backfill/__init__.py` | Registry `_SOURCES`, skip set, write loop, per-source summary |
| `src/stockroom/backfill/cursor_vscdb.py` | Today's only adapter — the worked example |
| `src/stockroom/backfill/__main__.py` | CLI |
| `tests/test_backfill.py` | Orchestrator, registry conformance, guard tests |
| `tests/test_backfill_cursor_vscdb.py` | Adapter-level tests |
| `tests/test_backfill_cli.py` | End-to-end subprocess runs |

## The Adapter Contract

An adapter is a module exporting five names, added to `_SOURCES` in `backfill/__init__.py`:

| Name | Contract |
| --- | --- |
| `NAME` | Registry key and `--source` value. Must equal its key in `_SOURCES` (e.g. `cursor-vscdb`) |
| `HARNESS` | Existing harness label. Scopes the skip set and labels the summary |
| `resolve_source(override)` | Returns the store path from flag → env → config. Raises `BackfillError` naming **all three** inputs when unconfigured |
| `candidates(source)` | Cheap id enumeration. Must not parse — the skip set is applied to this list, *before* the expensive work |
| `parse_all(source, ids)` | Yields `NormalizedSession` for those ids — the same contract ingest parsers produce |

Three rules the orchestrator relies on:

1. **Adapters never touch the warehouse.** No connection is passed in, and none should be opened. Every skip decision, write, and summary count belongs to the orchestrator.
2. **`candidates` is cheap and `parse_all` is not.** The split exists so a re-run skips already-present sessions without reading them. Collapsing the two throws that away.
3. **Fail soft, per record and per source.** One unparseable record is skipped, not fatal; one broken source does not stop the others. `parse_all` yields `None`-free results and simply omits what it cannot reconstruct.

A parametrized conformance test in `tests/test_backfill.py` runs over `_SOURCES`, so a new adapter is checked for all of this the day it lands.

## Adding One

1. **Write the adapter tests first**, in `tests/test_backfill_<source>.py`. Synthesize the store in-test rather than committing a binary fixture — see the `build_vscdb` factory in `tests/conftest.py` for the pattern.
2. **Write the adapter**, exporting the five names above. Give it a module docstring recording the store's shape; that store is undocumented by its vendor and the docstring is the only place that knowledge lands.
3. **Register it** in `_SOURCES`. The CLI's `--source` choices come from the registry, so nothing in `__main__.py` needs editing unless the source needs its own path flag (`--state-vscdb` is the precedent).
4. **Add a user-guide page** under `docs/user-guide/load/backfill/`, sibling to `cursor-vscdb.md`, and a row in that section's index table. Per-source read caveats and warehouse-column mappings belong there, not in the shared page.
5. **Run the gate**: `make ci` plus `make docs-build`.

## Trying It Against A Real Store

Backfill writes to the warehouse, so exercise it against a scratch one rather than your own:

```bash
STOCKROOM_HOME=/tmp/backfill-scratch stockroom migrate
STOCKROOM_HOME=/tmp/backfill-scratch stockroom backfill --source <name> --dry-run --verbose
STOCKROOM_HOME=/tmp/backfill-scratch stockroom backfill --source <name> --verbose
STOCKROOM_HOME=/tmp/backfill-scratch stockroom query "SELECT harness, count(*) FROM sessions GROUP BY 1"
```

`--dry-run` does everything but the write, which makes it the fast loop while a parser is still wrong; `--force` re-parses what the same source previously wrote, which is the loop after it is nearly right. A dry run goes through `warehouse.open_current()` — read-only, never migrating, no single-writer flock — so it needs a warehouse that already exists and is at schema head, which is why `stockroom migrate` is the first line above.

## Guard Tests You Must Not Weaken

Two tests in `tests/test_backfill.py` encode the "not nightly" invariant as an absence, which means nothing else will catch a regression:

* `schedule.render_payload()` contains no `backfill` token.
* The `stockroom.ingest` package source contains no import of `stockroom.backfill`.

The second matches the dotted import path rather than the bare word on purpose — the writer's own docstring has to *discuss* the backfill case to justify its run-clock fallback, and a guard that forbids naming what it protects against is one somebody weakens the next time they write a sentence.
