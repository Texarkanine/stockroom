---
task_id: token-usage-grain-rollups
date: 2026-07-19
complexity_level: 3
---

# Reflection: Token Usage Grain & Rollups

## Summary

Delivered dual-grain token storage (`sessions.*_tokens` + existing `messages.*_tokens`) and VIEW `session_token_usage` for conversation rollups, with ingest hooks that stay NULL for Claude/Cursor today. Succeeded against the brief without Cursor attribution creep.

## Requirements vs Outcome

All acceptance criteria met: Claude message tokens unchanged; documented rollup via VIEW; session-grain columns ready without destructive migration; tests cover schema/VIEW/writer; Cursor remains NULL at both grains. No requirements dropped. Additions beyond the numbered plan steps: `sr-query/SKILL.md` SQL examples (natural home for agents) and head-version pin bumps in warehouse/migrate tests (required for any new migration).

## Plan Accuracy

Sequence (schema TDD → migration → golden → writer TDD → model/writer → docs → verify) was correct. Preflight amendments (VIEW via `duckdb_views()`, split writer test/code steps, include SKILL.md) paid off. The main plan gap was not naming the `_HEAD_VERSION` / migrate-runner pin updates — they always accompany a new migration head and should be an explicit checklist item next time. Challenges that materialized matched the pre-mortem (SUM NULL semantics, snapshot including views via `duckdb_columns`); no architectural surprise.

## Creative Phase Review

Option B (dual typed columns + rollup VIEW) translated cleanly: one migration, thin ingest fields, read-only VIEW. No friction from COALESCE-per-column or `token_grain`. Rejecting a fact table and secondary index was correct for personal-scale DuckDB. The model dual-grain precedent (`model`/`models`) made the design feel like pattern completion rather than invention.

## Build & QA Observations

Build was smooth after TDD red/green cycles. Full suite initially failed only on stale head pins — mechanical, not design. QA found no semantic defects; docs and creative intent lined up with the code.

## Cross-Phase Analysis

Preflight's "lock VIEW explicitly" note prevented over-reliance on `_introspect_schema`; ironically the golden snapshot *also* captured VIEW columns because `duckdb_columns` lists them — belt and suspenders both useful. Creative Option B constrained build away from CSV/dashboard scope, so QA had little to prune.

## Insights

### Technical
- Adding a DuckDB VIEW at migration head updates both explicit view asserts *and* the cumulative golden when `_introspect_schema` reads `duckdb_columns` (views appear as "tables" there). Plan for both locks when introducing views.
- Head-version constants in `test_migrate_runner` / `test_warehouse_open` / `test_warehouse_concurrency` are part of every migration's blast radius — treat them as a required companion change, not an afterthought.

### Process
- Preflight amendments that encode TDD step ordering and assert paths reduce build thrash; keep that bar for L3 schema work.
- Nothing notable about phase overhead for this task — creative → plan → preflight → build → QA was proportionate.
