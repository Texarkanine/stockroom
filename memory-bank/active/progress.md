# Progress

Add a Skill Usage dashboard capability per [#63](https://github.com/Texarkanine/stockroom/issues/63): harness-extensible extraction + API endpoint, then several aggregate/compare chart mockups in the main dashboard so the operator can pick a visual before final layout placement.

**Complexity:** Level 3

## 2026-07-17 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - Intent clarified and approved (count every discrete skill use; mockups in main dashboard at Tool Usage size)
    - Complexity classified as Level 3
* Decisions made
    - User 10 + agent 5 uses of the same skill = 10 and 5 counts (no session-level dedupe)
    - Mockup phase embeds candidates in the main dashboard (1×1 like Tool Usage); placement next to Tool Usage is a follow-up after chart selection
* Insights
    - Skill identity lives in heterogeneous `tool_calls` / message shapes — per-harness Python extractors over filtered SQL rows match existing ingest adapter style better than one mondo query

## 2026-07-17 - PLAN - COMPLETE

* Work completed
    - Mapped dashboard metrics / static / test touchpoints
    - Probed warehouse for Claude user command-name, Skill tool, synthetic skill blobs; Cursor Read `…/SKILL.md`
    - Resolved open questions via creative: extractor architecture + three mockup encodings
    - Wrote ordered TDD implementation plan (10 steps)
* Decisions made
    - `/api/skills` payload: `{skills, invokers, calls: {harness: {user, agent}}}`
    - Module `stockroom.dashboard.skill_usage` with `EXTRACTORS` registry
    - Mockups: nested doughnut, stacked bar, tools-like — all in main grid at Tool Usage size with “(mockup)” titles
* Insights
    - Claude skill blobs must not count; Cursor presently has no discrete user-invoke event in the warehouse

## 2026-07-17 - PREFLIGHT - COMPLETE (PASS)

* Work completed
    - Checked TDD encoding, conventions, dependency impact, conflicts, completeness
    - Amended implementation plan: stricter test-before-code units; static panel ids; real-shaped fixtures
* Decisions made
    - No rearchitecture; proceed to build on amended plan
* Insights
    - `dashboard-data.test.mjs` and `test_dashboard_static.py` already pin endpoint/panel inventories — easy to miss without preflight
