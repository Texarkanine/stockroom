# Active Context

## Current Task: `sr-query` — raw SQL query surface over the warehouse (milestone 5 of `p1-data-backbone`, Level 2 sub-run)

**Phase:** PLAN - COMPLETE

## What Was Done

- Re-entered `/niko` on the `p1-data-backbone` L4 project. Milestone 4 (`project_id` + `cwd` recovery) was `REFLECT COMPLETE`; checked it off in `milestones.md` and cleared its sub-run ephemeral files per Step 2a. Preserved `milestones.md`, the L4 `projectbrief.md`, and prior `reflection/` docs.
- Classified the next unchecked milestone (`sr-query`) as **Level 2**: a single self-contained, user-facing read surface over the already-built, already-populated warehouse.
- **PLAN:** wrote the full L2 plan to `tasks.md` — 12 behaviors, a 10-step TDD plan building `src/stockroom/query.py` (`run_query` + `_format_table` + `main`) invoked as `python -m stockroom.query "<SQL>"`, read-only through `warehouse.open(read_only=True)`. Surveyed the surface (`warehouse.open`, the `ingest` con-injection convention, `test_ingest_cli.py` subprocess pattern, conftest fixtures) and the roadmap/tech-brief `sr-query` spec.

## Key Decisions

- **Engine surface only, no skill dir:** milestone 5 ships `python -m stockroom.query` (mirroring m3's `python -m stockroom.ingest`); the `skills/sr-query/` wrapper + per-harness `/sr-query` invocation are explicitly Phase 5 work. Out of scope keeps this L2.
- **Read-only by construction:** the query surface opens read-only — the warehouse is rebuildable ETL output and this surface is for interrogation, so DuckDB rejects writes through it. The lazy migration gate still runs (reader-becomes-migrator).
- **Single module, no package:** `stockroom/query.py` is directly runnable via `python -m stockroom.query` — no `__main__.py` (unlike the multi-module `ingest` package). KISS.
- **One output format (no `--format` flag):** a deterministic text table via an isolated, unit-tested `_format_table` — YAGNI on richer formats.

## Next Step

- PLAN → PREFLIGHT is autonomous (solid edge) in the L2 workflow. Proceed to PREFLIGHT (`niko-preflight` skill).
