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
