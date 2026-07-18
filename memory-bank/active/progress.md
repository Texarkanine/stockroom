# Progress

Ship dashboard model analytics for [#67](https://github.com/Texarkanine/stockroom/issues/67) / [#68](https://github.com/Texarkanine/stockroom/issues/68), then address selected PR #70 rework: message-`ts` bucketing for `model_trends`, and time-only First-Prompt range labels.

**Complexity:** Level 2

## 2026-07-18 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - Confirmed intent: do #67 and #68 together
    - Classified Level 3 (multi-component feature with creative decisions; not system-wide architecture)
* Decisions made
    - Pair the issues in one task (`dashboard-model-analytics`) rather than sequencing #68 alone first
* Insights
    - Shared dual-grain attribution (session set vs message counts) and Cursor NULL honesty are the main coupling between the two issues

## 2026-07-18 - CREATIVE - COMPLETE (dual-grain attribution)

* Work completed
    - Explored recorded-only vs sole-model fallback vs fan-out vs proportional split
* Decisions made
    - **Sole-session-model fallback** for message grain (assistant turns); conversation grain keeps union once-per-session
* Insights
    - Multi-model Cursor stays conversation-only for message grain — honest, not inflated

## 2026-07-18 - CREATIVE - COMPLETE (top-models + over-time UI)

* Work completed
    - UI/UX options for #67 and #68 against shipped dashboard design system
* Decisions made
    - #67: two half-width bars with grain in titles
    - #68: two `panel-wide` stacked areas (conversation + message); Compare filters harnesses into the stack, does not add harness×model stacks
    - Shared per-model colors across model panels

## 2026-07-18 - PLAN - COMPLETE

* Work completed
    - Full L3 plan in `tasks.md`: dual-grain `/api/models` + `/api/model_trends`, TDD map, 8 implementation steps
* Decisions made
    - Clean-break `/api/models` payload (`by_conversation` / `by_message`); areas return harness-summed model series
* Insights
    - Attribution helper must land before UI so bars and areas cannot diverge

## 2026-07-18 - PREFLIGHT - COMPLETE (PASS)

* Work completed
    - Validated TDD encoding, conventions, consumers, completeness
    - Amended plan: `model_usage.py`, per-step test-first ordering, no docs step
* Decisions made
    - Attribution lives in `dashboard/model_usage.py` (skill_usage parallel)
* Insights
    - Untracked `.cursor/skills/stockroom-local/` mirrors engine tree — not a consumer; do not edit

## 2026-07-18 - PLAN AMENDMENT - OPERATOR LAYOUT

* Work completed
    - Recorded widget order; amended #68 creative + `tasks.md` (single conversation over-time area; write-read `panel-wide` after efficiency/first-prompt)
* Decisions made
    - Over-time grain = conversation (pairs with left bar); message grain = right ranking chart only
* Insights
    - Preflight still PASS — layout amendment, not rearchitect

## 2026-07-18 - BUILD - COMPLETE

* Work completed
    - `model_usage` attribution helper; dual-grain `models()`; `model_trends()` + ENDPOINTS
    - Client fetch, panel builders (`colorForModel`), HTML grid, render wiring
    - Full verify: dashboard py/js + `make test` green
* Decisions made
    - Attribution test file named `test_dashboard_model_usage.py` for Make target glob
    - Aggregate model bars use per-model `colorForModel` colors; compare keeps harness stacks
* Insights
    - Dataset `fill: true` is enough for stacked area; Write/Read stays `fill: false` via `lineDataset`

## 2026-07-18 - QA - COMPLETE (PASS)

* Work completed
    - Semantic review vs plan/creatives; no debris/TODOs; completeness confirmed
    - DRY fix: shared `_model_attribution_inputs` for `models()` + `model_trends()`
* Decisions made
    - Keep unused `_selected/_mode/_colors` on area builder for panel-signature parity
* Insights
    - Dual endpoints share one window load; ranking/bucketing stay thin wrappers

## 2026-07-18 - REFLECT - COMPLETE

* Work completed
    - Wrote `reflection/reflection-dashboard-model-analytics.md`
    - Reconciled persistent files (no updates)
* Decisions made
    - None beyond reflection content
* Insights
    - Attribution-first + shared window load; dashboard test glob naming; layout amendments can stay plan-level

## 2026-07-18 - REWORK INITIATED

* Work completed
    - Operator chose rework from post-reflect / PR #70 CodeRabbit review (judge: items 2 + 4 only)
* Operator feedback (PR #70)
    - **Fix 2**: Bucket `model_trends` by message `ts` when present, else session activity; carry timestamp through attribution; add multi-day coverage (`discussion_r3609260655`)
    - **Fix 4 (amended)**: First-Prompt `.panel-range` is time-range only for all presets — remove “Average session length by prompt detail · …” from corner text; that meaning belongs in the panel tooltip/help if needed (`discussion_r3609260661`, operator override)
* Explicitly out of scope for this rework
    - Item 1 (`tasks.md` stale grain docs), Item 3 (sole-model dedupe), Item 5 (reflection nitpick)
* Decisions made
    - Rework disposition; clear stale plan/context status files and reclassify

## 2026-07-18 - COMPLEXITY-ANALYSIS - COMPLETE (rework)

* Work completed
    - Classified rework as Level 2 (bug/correctness fixes across metrics + static UI; known approach from creative + review)
* Decisions made
    - Not Level 1: touches `model_usage` / `metrics` / JS labels / HTML seed / tests
    - Not Level 3: no new feature or open design exploration beyond operator-specified Fix 4 label policy
* Insights
    - Message-`ts` bucketing was already contracted in `creative-dual-grain-attribution.md`; implementation lagged the message-grain polish

## 2026-07-18 - PLAN - COMPLETE (rework)

* Work completed
    - TDD plan: message-`ts` through `MessageRow` / `attributed_turns`; `model_trends` bucket key; time-only firstPrompt labels + HTML seed
* Decisions made
    - Keep session-activity window filter; only change bucket key to message `ts` when present
    - Explanatory First-Prompt copy stays in `PANEL_HELP`, not `.panel-range`
* Insights
    - `attributed_turns` 4-tuple is the smallest way to carry `ts` without duplicating attribution in `model_trends`

## 2026-07-18 - PREFLIGHT - COMPLETE (PASS, rework)

* Work completed
    - Validated TDD encoding, consumers, conventions; amended plan for per-step test-first wording
* Decisions made
    - No advisory redesign — stick to creative message-time-first + operator time-only range labels
* Insights
    - `skill_usage.MessageRow` is unrelated; do not conflate

## 2026-07-18 - BUILD - COMPLETE (rework)

* Work completed
    - Message-`ts` through attribution; `model_trends` message-time-first bucketing + tests
    - First-Prompt range labels time-only (JS + HTML seed); help text retained
    - Full verify green
* Decisions made
    - Window filter stays session activity; only bucket key uses `ts`
    - No `PANEL_HELP` rewrite — existing copy already covers average session message count by prompt bucket
* Insights
    - Existing composer fixtures already covered null-`ts` fallback once SELECT carried `m.ts`

## 2026-07-18 - QA - COMPLETE (PASS, rework)

* Work completed
    - Semantic review vs rework brief/plan; no KISS/DRY/YAGNI/completeness gaps
* Decisions made
    - None — clean build
* Insights
    - Carrying `ts` on `MessageRow` kept attribution pure and metrics thin

## 2026-07-18 - REFLECT - COMPLETE (rework)

* Work completed
    - Wrote `reflection/reflection-dashboard-model-analytics-pr70-rework.md`
    - Reconciled persistent files (no updates)
* Decisions made
    - None beyond reflection content
* Insights
    - Grain flips and bucket-key contracts should ship together
