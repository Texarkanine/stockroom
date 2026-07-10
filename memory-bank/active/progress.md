# Progress

Add top-bar date-range selector wired to windowed `since`/`until` (prior-period % deltas + panel labels) and restyle Aggregate/Compare as an exclusive segmented toggle (#4, #5).

**Complexity:** Level 3

## 2026-07-10 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - Classified first unchecked L4 milestone (m1: #4 + #5) as Level 3
* Decisions made
    - Not a bug fix; enhancement spanning controls strip, request-plan/`since`/`until` wiring, prior-window KPI deltas, panel labels, and Aggregate/Compare CSS/ARIA — multiple components → L3
    - Aligns with milestones.md advisory estimate for m1
* Insights
    - Design choices on date-range UX (presets vs free-form) are expected to surface in plan/creative; preflight advisory preferred presets with clean prior-window math

## 2026-07-10 - CREATIVE (date-range UX) - COMPLETE

* Work completed
    - UI/UX exploration for date-range control; documented in `creative/creative-date-range-ux.md`
* Decisions made
    - Preset exclusive control: Default | 7d | 30d | 90d | 1y; initial Default (omit bounds)
    - Always send both `since`/`until` when a preset is active; no URL sync / persistence / free-form calendar in m1
* Insights
    - Preserves mixed endpoint defaults until operator opts in; prior-window math stays operator-obvious

## 2026-07-10 - PLAN - COMPLETE

* Work completed
    - Component analysis across dashboard static modules + test surfaces
    - Creative decision integrated; full TDD + implementation plan written to `tasks.md`
* Decisions made
    - Optional bounds arg on request plan/fetch; label helper for honest panel ranges
    - No new dependencies; Python metrics/server unchanged for m1
* Insights
    - Main risk is dishonest static labels after bounds land — treated as first-class test/ impl step

## 2026-07-10 - PREFLIGHT - COMPLETE

* Work completed
    - Validated m1 plan against dashboard static/data/core/test layout
    - Amended TDD encoding (explicit test-before-code on steps 1–3; step 4 glue-only) and `options.window` API alignment
    - Wrote `.preflight-status` = PASS
* Decisions made
    - No rearchitect; server remains out of scope for m1
* Insights
    - Advisory: URL-synced range would help shareable views but was explicitly deferred in creative — leave for a later issue

## 2026-07-10 - BUILD - IN-PROGRESS

* Work completed
    - Preflight PASS confirmed; entering build for m1 top controls
* Decisions made
    - Execute plan steps 1–4 in order with TDD (tests before code on 1–3; adapter glue last)
* Insights
    - None yet

## 2026-07-10 - BUILD - COMPLETE

* Work completed
    - Request-plan bounds via `options.window` (wrapped excluded)
    - View-state `daterange` action, `resolveWindowBounds`, `panelRangeLabels`
    - Static `#date-range-selector` + segmented mode/date controls
    - Adapter wiring: busy disable, fetch window, honest panel labels
    - Verification: `make test-js` (38), dashboard pytest, full `make ci` green
* Decisions made
    - Shared `.segmented` pill styling for date-range and mode fieldsets
    - No server changes; no plan deviations
* Insights
    - Keeping label/bounds logic in core made adapter glue thin and low-risk

## 2026-07-10 - QA - COMPLETE

* Work completed
    - Semantic review against plan + creative-date-range-ux
    - Trivial fixes: un-export unused preset helpers; JSDoc wording
    - Wrote `.qa-validation-status` = PASS
* Decisions made
    - No substantive issues; no return to build/plan
* Insights
    - Export surface discipline still worth a QA pass even on thin adapters

## 2026-07-10 - REFLECT - COMPLETE

* Work completed
    - Wrote `reflection/reflection-dashboard-polish-m1-top-controls.md`
    - Reconciled persistent files: no updates required
* Decisions made
    - Next operator step is `/niko` (L4 milestone advance), not archive
* Insights
    - Core/data vs adapter split and static-contract TDD step both validated for control-strip work
