# Active Context

## Current Task: Phase 2 · Milestone 3 — `sr-search` (`p2-embeddings-search`, sub-run m3)

**Phase:** `PLAN - COMPLETE` (incl. 3 autonomous creative explorations, all high-confidence). Plan written to `tasks.md`; awaiting operator-initiated **Preflight**.

## What Was Done

- Classified m3 (`sr-search`) **L3** and built the full plan test-first.
- Probed the one load-bearing unknown (keyword mechanism): DuckDB 1.5.4 `ILIKE` built-in/correct; `fts` un-bundled + stale-on-insert.
- Resolved 3 open questions via creative docs:
  - **Keyword** → `ILIKE` (not FTS) — `creative-keyword-search-mechanism.md`.
  - **Routing+fusion** → blend-by-default + `--mode`, fused with **RRF**; "SQL" = keyword path (no NL→SQL) — `creative-search-routing-and-fusion.md`.
  - **Truncation** → detail levels `compact|snippet|full` (default `snippet`), render-only trim — `creative-read-time-truncation.md`.
- Plan: new `stockroom.search` module; one additive `run_semantic_search(harness=None)` change; **no schema/migration**; ~30-behavior TDD plan; 8 test-first steps.

## Key Decisions (recorded)

- `sr-search` *is* the blend; `sr-query`/`sr-semantic` remain the pure escape hatches — no clever auto-router (honesty over cleverness).
- Keyword-only mode requires no torch (lazy encoder).
- `--harness` is the per-harness filter m2 deferred; total-output `--budget` truncation is a deferred future enhancement.
- No-truncation-at-rest preserved: `SearchHit.text` is whole; trimming lives only in the render path.

## Next Step

- 🧑‍💻 Operator runs **`/niko-preflight`** to validate the plan before the build phase.
