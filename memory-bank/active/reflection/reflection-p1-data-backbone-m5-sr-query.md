---
task_id: p1-data-backbone-m5-sr-query
date: 2026-06-28
complexity_level: 2
---

# Reflection: `sr-query` — raw SQL query surface over the warehouse

## Summary

Shipped `python -m stockroom.query` — a single runnable module that opens the warehouse read-only through the `warehouse.open()` chokepoint, runs arbitrary SQL, and prints a column-aligned table with a `(N rows)` trailer. It succeeded cleanly: green `make ci` (184 passed, 16 new), QA PASS with no rework. This closes Phase 1 — the schema → migration framework → ingest → query loop is now demonstrably end-to-end.

## Requirements vs Outcome

Delivered exactly what the roadmap/tech-brief asked: raw SQL against the warehouse, the first user-facing read surface, proving the database is real and queryable end to end. No requirements dropped or reinterpreted. One in-scope addition from preflight (amendment A2): `_format_table` always emits a `(N rows)` trailer, making the proof-of-queryability output self-describing. The `skills/sr-query/` skill wrapper + per-harness invocation were deliberately scoped out (Phase 5) and that boundary held — the milestone stayed L2.

## Plan Accuracy

The plan was accurate end-to-end: the 10-step sequence, the file list (`query.py` + two test files + two doc files), and the identified challenges (missing-warehouse handling, no-result-set `description`, output-format scope creep) were exactly what materialized. No steps needed reordering, splitting, or adding. The preflight A1 amendment (per-step RED→GREEN) made the TDD execution mechanical. Unlike milestone 4 (where introducing `0002` flipped the migration head and forced a one-commit collapse), this milestone was purely additive — no shared global to disturb — so the planned per-step commits could have stood alone; they were folded into one feature commit only for narrative cohesion, not necessity.

## Build & QA Observations

Build was smooth and fast: every step went RED→GREEN on the first implementation. The only wrinkle was a benign RED false-positive — the empty-SQL CLI test passed during the red run because the stubbed `main` raised `NotImplementedError` (nonzero exit), then became a genuine pass once `main` shipped. QA was clean (no fixes); the build integrated as a natural extension of the chokepoint rather than an accretion layer, so the mechanical and semantic gates agreed.

## Insights

### Technical

- **Read-only is enforcement-for-free.** Opening `read_only=True` lets DuckDB reject writes through the query surface — no app-level statement allow/deny-list to build, test, or get wrong. The "escape hatch" stays safe by construction, and the CLI only has to translate the resulting `duckdb.Error` into a clean message. This generalizes: any pure read surface over the warehouse should open read-only and lean on the engine for immutability.
- **`python -m` module-vs-package is a real design lever.** A single-file `stockroom/query.py` is directly runnable (no `__main__.py`), which is the right shape for a cohesive one-surface tool — reserving the package + `__main__.py` form (as `ingest` uses) for genuinely multi-module subsystems.

### Process

- **A purely additive milestone is the cheap case** — and recognizing that up front (no shared global, no migration head, no cross-module rename) is what justified holding it at L2 and predicted the clean build. The contrast with m4's migration-head coupling is the signal: scope risk lives in shared mutable globals, not in line count.

### Million-Dollar Question

What we built is essentially the elegant solution. Had a read-only query surface been a foundational assumption from the start, the only thing that might have changed is that `warehouse.open()`'s docstring (which already names `sr-query` as a consumer) would have been written knowing the reader-degradation/lazy-migrate path would be exercised by an interactive surface, not just by ingest — but the chokepoint design already anticipated exactly this, so no redesign emerges. The Phase-1 ordering (query last, over already-built infrastructure) is what made this milestone small.
