# Progress

Rework the shipped skill-usage mockups: sunburst nested encoding (agent-led colors), Skill/Tool **Distribution (top 10)** naming, and stacked tooltip color parity. Continues [#63](https://github.com/Texarkanine/stockroom/issues/63) mockup evaluation.

**Complexity:** Level 2

> Prior lifecycle was Level 3 (initial skill-usage mockups). This rework is classified Level 2.

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

## 2026-07-17 - BUILD - COMPLETE

* Work completed
    - `skill_usage` extractors + registry; `metrics.skills` + `/api/skills`
    - Client fetch, three mockup panel builders, HTML/render wiring
    - Full dashboard + project test suites green; lint/format clean
* Decisions made
    - Nested compare uses stacked harness×invoker bar (creative-allowed readability tradeoff)
    - Candidate SQL stays coarse; skill naming only in extractors
* Insights
    - Ranking by total across invokers means a skill with user+agent events outranks single-invoker peers (expected; covered in mix test)

## 2026-07-17 - QA - COMPLETE (PASS)

* Work completed
    - Semantic review against plan + creative (KISS/DRY/YAGNI/completeness/regression/integrity/docs)
    - Trivial KISS fix: `skills()` iterates `names` only (candidates already filtered)
* Decisions made
    - Kept duplicate `_parse_tool_input` in `skill_usage` (avoids circular import with metrics)
    - No user-guide update (plan: endpoint not cataloged there)
* Insights
    - Nested doughnut length mismatch (skills vs invokers) is intentional mockup debt, not a contract bug

## 2026-07-17 - REFLECT - COMPLETE

* Work completed
    - Full lifecycle reflection written
    - Persistent files scanned — no updates
* Decisions made
    - Final chart pick + layout placement remain follow-up after operator review of mockups
* Insights
    - Dashboard endpoint/panel inventory pins are part of the contract for new metrics UI work

## 2026-07-17 - REWORK INITIATED

* Operator chose rework (not archive) with addon scope:
    - Nested mockup must be a **sunburst** (invoker groups aligned; skills nest under user/agent; same skill can appear on both sides)
    - Agent-led palette: solid on agent side; user side = faded twins; user-only skills take next free palette slot
    - Fix stacked-bar tooltip swatches to match legend/bar fills
    - Rename panels to **Tool Distribution (top N)** and **Skill Distribution** (same “Distribution” language; skill panels show top-N clarity too)
* Post-reflect extraction fixes (Cursor `manually_attached_skills`, Claude built-in denylist, doughnut nearest tooltips) remain in the tree and are in scope to keep

## 2026-07-17 - COMPLEXITY-ANALYSIS - COMPLETE (rework)

* Work completed
    - Classified rework as Level 2 (dashboard UI subsystem; encoding already agreed)
* Decisions made
    - No API/schema change for sunburst — client reshapes `/api/skills` series
    - Titles use concrete `(top 10)` matching default `limit=10`
* Insights
    - Chart.js sunburst alignment needs outer data ordered `[…user skills…, …agent skills…]` with inner `[userTotal, agentTotal]` sharing one circumference

## 2026-07-17 - PLAN - COMPLETE (rework)

* Work completed
    - TDD plan: sunburst builder tests → tooltip labelColor → Distribution (top 10) titles → verify
* Decisions made
    - Compare mode stays stacked bar; only aggregate nested becomes sunburst
    - Legend may list skill·invoker or favor tooltips — called out as Challenge
* Insights
    - Circumference-sum assertions in tests are the load-bearing guard against “two independent pies”

## 2026-07-17 - PREFLIGHT - COMPLETE (PASS)

* Work completed
    - Tightened TDD encoding on tooltip + title steps; confirmed `renderChart` title strings
* Decisions made
    - Proceed to build on amended plan
* Insights
    - Prior creative nested-doughnut doc is historical; rework brief owns sunburst

## 2026-07-17 - BUILD - COMPLETE

* Work completed
    - Rebuilt nested aggregate as aligned sunburst with `assignSkillSunburstColors`
    - Added `tooltipLabelColors` and wired Chart.js `labelColor` callback
    - Renamed Tool/Skill Distribution panels with `(top 10)` / skill encoding + mockup
    - Full dashboard JS/PY + project suite green; format/lint clean
* Decisions made
    - Outer skill labels stay bare names (duplicate when dual-invoker); circumference tests guard alignment
    - Nested title encoding cue is `(sunburst)`
* Insights
    - Chart.js default tooltip swatch prefers border; forcing fill on both stroke and fill fixes stacked invoker bars without per-panel special cases
