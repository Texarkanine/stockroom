# Progress

Ingest Cursor Agent CLI chats under `harness='cursor'`, pass through Claude native `entrypoint`, add `sessions.entrypoint`, and dedupe Cursor id collisions preferring `store.db` — warehouse/SQL only, no dashboard UI.

**Complexity:** Level 3

## 2026-07-21 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - Intent clarified and approved
    - Source/warehouse research completed (chats store.db, agent-transcripts, Claude entrypoint)
    - Complexity classified as Level 3
* Decisions made
    - No dashboard UI in this task
    - Linux roots only; no WSL/Windows multi-home discovery
    - Synthesize Cursor entrypoint from provenance (`cli` / `ide`); no system-prompt heuristics
    - On Cursor id collision, prefer chats `store.db` over agent-transcripts
* Insights
    - Claude desktop already writes the same JSONL shape with `entrypoint: claude-desktop`
    - Cursor has no native entrypoint field; path is sufficient for CLI certainty

## 2026-07-21 - CREATIVE - COMPLETE

* Work completed
    - Resolved store.db parse algorithm (ordered root-hash walk)
* Decisions made
    - Parse `latestRootBlobId` as repeated 32-byte protobuf bytes fields for conversation order; JSON user/assistant leaves only
* Insights
    - Root blob is already a linear id list — full graph BFS unnecessary

## 2026-07-21 - PLAN - COMPLETE

* Work completed
    - Component analysis, TDD plan, implementation steps, challenges, pre-mortem written to `tasks.md`
* Decisions made
    - Dual Cursor roots with separate `_sync_state` watermarks; filter transcripts when chats id present
    - No new dependencies
* Insights
    - `_sync_state (harness, source_root)` already supports a second Cursor root without schema change

## 2026-07-21 - PREFLIGHT - COMPLETE

* Work completed
    - Validated TDD encoding, conventions, dependency impact, completeness
    - Amended plan for orchestrator/golden test files and docs paths
* Decisions made
    - Preflight PASS — build gated on operator `/niko-build`
* Insights
    - Dashboard `SELECT s.*` will surface `entrypoint` passively; still no filter/legend work
