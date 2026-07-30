---
task_id: conversation-summary-tool-skill-pie-charts
complexity_level: 3
date: 2026-07-29
status: completed
---

# TASK ARCHIVE: Per-Conversation Tool/Skill Composition Charts

## SUMMARY

Added per-conversation tool-call and skill-use distribution doughnut charts to the dashboard session view ([issue #107](https://github.com/Texarkanine/stockroom/issues/107)), plus a matching advanced query recipe so the same insight is available outside the UI. The session view was restructured into the operator-selected "F-a" layout: an overview pill (session metrics + Tools/Skills composition charts) above a messages-only card (toolbar → conversation title → turns). A Level 1 rework pass followed operator UAT: empty composition panels collapse to a compact "none found" signal instead of full-height blank boxes, session doughnuts were densified (176px + right legend), and a shrink FOUC on session load was eliminated. Shipped via draft [PR #108](https://github.com/Texarkanine/stockroom/pull/108) on `per-convo-dials`.

## REQUIREMENTS

From the project brief:

1. Visualize skill-call distribution per conversation on the dashboard conversation overview.
2. Visualize tool-call distribution per conversation on the same overview.
3. Include an advanced query recipe covering this insight.
4. Before locking placement: internet prior-art scan + HTML mockups of candidate placements; operator picks visually (visual UAT gate).
5. Fit the existing dashboard visual language; reuse existing warehouse/API data; empty/sparse sessions degrade gracefully.

Rework requirements (post-UAT):

1. Empty composition panels must not reserve full doughnut height — compact "none found" signal, distinguishable from a load/render failure.
2. Bounce/`--replace` the local dashboard after building so live UAT matches current code.
3. Session composition doughnuts denser than metrics-pane defaults (shorter height, side legend) so the transcript starts higher.
4. No shrink FOUC: wraps must not paint at metrics height then collapse after the session fetch.
5. Out of scope: visitor/per-harness query-object rewrite — the implementation already loads one `(harness, session_id)` and aggregates in memory.

## CREATIVE PHASE DECISIONS

**Design question:** where does per-session composition live on the session view? Operator required a visual pick from mockups, making this the L3 driver.

**Prior art scanned:** header usage stats (PocketDev, AgentsView); transcript + sidebar (Helvia). Metrics pane already teaches the doughnut language for tools/skills globally; session view was meta + chat only in a `min(1200px)` centered column with no side rail.

**Options mocked** (`mockups-session-distribution.html`, dashboard design tokens, served locally for click-through UAT):

- **A · Side column:** sticky ~240px composition rail as a sibling outside the conversation card. First mock wrongly nested it inside the message card; even revised, operator rejected it — sticky rail still wastes width.
- **B · Inline above:** full-width summary band under session meta, inside the conversation card. Operator liked its simplicity; both independent unseeded model picks (GPT `gpt-5.6-sol-high`, Opus `claude-opus-5-thinking-high`) chose B with A as runner-up, framing composition as a once-on-entry summary that should not permanently tax the transcript.
- **C · Slide-in drawer:** sticky viewport-edge handle sliding in a higher-z panel. (Operator's "popover" meant edge-affordance + slide-over, not disclosure expand-in-place.)
- **D · Header dials:** dropped by operator — not desired.
- **E / E-2 · Full-width charts card** below or above the conversation card, echoing the metrics dashboard scale.
- **F · Split pills:** session meta pill + Tools & Skills pill above; conversation card is messages only.

**Decision: F, refined to F-a** (operator visual pick):

1. Overview pill with no "conversation overview" page header: **session** (harness, model, tokens, started) then **composition** (Tools & Skills charts only, no prose), same visual language as the main metrics dashboard.
2. Messages pill: copy/export toolbar at top, then conversation title (when present) as the card heading, then turns. (F-b — toolbar between pills — rejected.)
3. Accepted tradeoff: charts scroll away with the overview; composition is glance-once.

**Friction discovered in implementation:** none against F-a itself — the layout translated cleanly. The empty-state behavior (creative note said "hide composition section or show empty-state without broken charts") is where the rework landed: the initial build showed empty panels at full doughnut height.

## IMPLEMENTATION

**Feature (L3):**

- **API:** `session_detail` extended to return the session `title` (already in schema, previously omitted) plus tools/skills aggregates. Skills derived via `skill_usage.iter_skill_uses` on session-scoped rows; tools aggregated from nested `tool_calls`. Payloads use the same harness-keyed `calls` shape as `/api/tools` / `/api/skills` even for a single session, because the panel builders (`buildToolsPanel`, `buildSkillsNestedPanel`) do not special-case "single session."
- **UI:** session pane split per F-a into overview pill (metrics band + composition charts, Chart.js doughnuts reused from the metrics pane) and messages-only card. Overview meta band is harness/model/tokens/started only.
- **Docs:** advanced query recipe for per-session tool/skill distribution; later folded into `tools.md` and the skills-cursor/claude "One session" sections (peer recipe file and docs symlink deleted, indexes updated).
- **Key files:** `skills/sr-search/src/stockroom/dashboard/` server (`session_detail`), `static/dashboard-core.mjs`, `static/dashboard.mjs`, `static/index.html`, `tests-js/dashboard-core.test.mjs`, Python dashboard tests, cookbook/docs pages.

**Rework (L1) + follow-ups:**

- `chartWrapLayoutStyle(empty, height)`: collapses a chart wrap to `0px` height when the model is empty, explicitly clearing the CSS `min-height: 260px` floor that otherwise defeats shorter heights. Applied to **all** chart panels, not just session composition — the tall-empty-box debt existed everywhere. Empty copy still shown.
- `withSessionCompositionLayout`: session Tools/Skills doughnuts at height 176 with `legendPosition: "right"`; main metrics doughnuts unchanged.
- FOUC fix: session composition wraps default to CSS `height: 0` and expand to 176 only when data paints; `resetSessionCompositionCharts` on session load clears prior doughnuts and avoids false empty copy. Initial state lives in CSS because the session pane is visible before its fetch resolves.
- Deleted CSS/constant/function-name source-string assertions added under always-tdd pressure, per [.cursor-rules#95](https://github.com/Texarkanine/.cursor-rules/issues/95); kept executable unit tests on the layout helpers. Relatedly, `test_dashboard_static.py` was stripped 15 → 5 tests (SLOBAC + #95): kept offline/load-order, a11y, radio control contracts, markdown-it hardening, and the #91 fixed-popover check.

**Rework root cause worth recording:** the "empty charts" report that opened the rework was a stale dashboard process on `:58008` started before the feature landed — fresh `session_detail` already returned correct tools/skills. Only the full-height empty panels were a real code defect.

## TESTING

- TDD throughout: API tests written ahead of `session_detail` changes (preflight verified the TDD encoding); JS unit tests for `chartWrapLayoutStyle` and `withSessionCompositionLayout`.
- Full suite green at feature build, at rework build, and re-run after the post-QA follow-ups: 119 dashboard JS tests (`make test-dashboard-js`), 793 passed / 4 skipped Python (`make test`).
- `/niko-qa` semantic review passed twice: once against the F-a plan/creative (no substantive fixes) and once against the rework brief.
- Operator visual UAT on the live dashboard (after `stockroom dashboard --replace`) drove the rework and both follow-ups (density, FOUC), and confirmed the final state.
- PR feedback triage on [#108](https://github.com/Texarkanine/stockroom/pull/108): fixed Greptile's orphaned JSDoc on `buildSessionMetaEntries` (c4762bd); dismissed CodeRabbit nits on ephemeral memory-bank files and LlamaPReview's request to restore static panel locks (#95/SLOBAC).

## LESSONS LEARNED

- Session-scoped Chart.js payloads must use the same harness-keyed `calls` shape as warehouse-window metrics even with one harness present — the panel builders don't special-case a single session.
- A collapse helper has to clear `min-height`, not just set `height`: a CSS `min-height` floor silently defeats any shorter inline height.
- Anything that must not flash needs its initial state in CSS/HTML, not the JS render path. The session pane paints before its fetch resolves, so "render it small on first paint" is too late by definition.
- For "the UI is empty" reports against a locally-served dashboard, bounce the process (`stockroom dashboard --replace`) before suspecting the data path. Skipping that cheap check cost the rework its entire initial framing — an architectural query rewrite was scoped for a stale-module bug.
- For placement debates, HTML mockups the operator can click beat prose options; locking F-a after mockups avoided a mid-build layout rewind. Operator visual UAT changed the product shape more than internet prior art did.

## PROCESS IMPROVEMENTS

- always-tdd pressure produced source-string greps on CSS values and function names — the same failure shape as the PR-template heading tests in [#106](https://github.com/Texarkanine/stockroom/pull/106). Executable tests on helpers carry the regression value; asserting a literal appears in a stylesheet only locks the implementation's prose. Tracked upstream as [.cursor-rules#95](https://github.com/Texarkanine/.cursor-rules/issues/95).
- The L3 creative low-confidence stop (operator must pick visually) prevented building the wrong placement; unseeded independent model picks were a cheap sanity input but the operator's pick (F) differed from both — treat model picks as advisory only.
- Post-QA follow-ups from live UAT (density, FOUC) suggest a live-UI check belongs before QA sign-off for dashboard work, not after.

## TECHNICAL IMPROVEMENTS

- Million-dollar question from the rework reflection: if "panels vary in height, legend position, and empty behavior" had been foundational, chart sizing would be one declarative layout descriptor per panel — height, legend position, empty collapse — resolved once at render time. Instead there's a default 280px wrap, inline overrides, a CSS `min-height` floor that fights them, and a reset function for first paint. `withSessionCompositionLayout` is the seed of that descriptor; the elegant version routes every panel through it.

## NEXT STEPS

- Draft [PR #108](https://github.com/Texarkanine/stockroom/pull/108) is still open on `per-convo-dials`; mark ready and merge when satisfied.
- Optional `#composition` deep-link was deferred at preflight (advisory only) — revisit if wanted.
