# Progress

Make token usage first-class for Claude Code (already message-grain) with easy conversation rollups, while keeping a cheap path for future harnesses that report session-level totals only. Do not pursue Cursor usage attribution.

**Complexity:** Level 3

## 2026-07-19 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - Intent clarified and approved
    - Researched Claude vs Cursor token sources and existing `messages.*_tokens` ingest
    - Ruled out joinable mapping from Cursor dashboard CSV to warehouse sessions
    - Complexity determined as Level 3
* Decisions made
    - Cursor CSV/API enricher is out of scope for this task
    - Message-grain remains source of truth when the harness reports that grain; do not fabricate message splits from session totals
* Insights
    - Claude path is largely ingest-complete; remaining value is rollup ergonomics + schema future-proofing for session grain

## 2026-07-19 - CREATIVE - COMPLETE

* Work completed
    - Architecture creative on dual-grain token storage & rollup surface
* Decisions made
    - Option B: nullable `sessions.*_tokens` + `session_token_usage` VIEW with native vs from_messages vs COALESCE effective totals; no extra index; no fact table
* Insights
    - 0001 already solved cross-grain metrics via `messages.model` vs `sessions.models`; tokens should mirror that

## 2026-07-19 - PLAN - COMPLETE

* Work completed
    - Component analysis, TDD test plan, ordered implementation steps for migration/VIEW/ingest/docs
* Decisions made
    - Implementation follows creative Option B; no dashboard/CSV scope
* Insights
    - Most user-visible gap is rollup ergonomics + explicit session-grain columns, not new Claude parsing

## 2026-07-19 - PREFLIGHT - COMPLETE

* Work completed
    - Validated plan against schema/ingest/docs conventions; amended TDD encoding and VIEW locking
* Decisions made
    - Preflight PASS; build gated on `/niko-build`
* Insights
    - `_introspect_schema` does not lock views today — VIEW needs explicit asserts alongside any golden snapshot

## 2026-07-19 - BUILD - COMPLETE

* Work completed
    - Implemented dual-grain session tokens + `session_token_usage` VIEW per creative Option B
    - TDD: schema 0007 tests/migration/golden, writer/model persistence + VIEW integration, docs
    - Full suite green (617 passed)
* Decisions made
    - Also updated `skills/sr-query/SKILL.md` (SQL home) alongside planned `sr-search` routing note
    - Bumped head-version pins in warehouse/migrate tests (routine migration follow-on)
* Insights
    - `_introspect_schema` via `duckdb_columns` includes VIEW columns, so `0007_snapshot.json` locks VIEW shape too

## 2026-07-19 - QA - COMPLETE

* Work completed
    - Semantic review vs plan, creative Option B, acceptance criteria, and system patterns
* Decisions made
    - QA PASS — no KISS/DRY/YAGNI/completeness/regression/integrity/docs defects requiring rework
* Insights
    - Implementation stayed on the dual-grain + VIEW surface; no Cursor attribution creep
