# Progress

Ship dashboard model analytics for [#67](https://github.com/Texarkanine/stockroom/issues/67) (top models by conversation and by message) and [#68](https://github.com/Texarkanine/stockroom/issues/68) (stacked area model usage over time) as one Level 3 effort on the existing offline dashboard stack.

**Complexity:** Level 3

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
