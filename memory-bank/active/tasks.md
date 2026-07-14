# Task: fix-dashboard-horizontal-tooltip

* Task ID: fix-dashboard-horizontal-tooltip
* Complexity: Level 1
* Type: bug fix

## What broke

Horizontal bar charts (Model Distribution, Sessions by Project, Tools-in-compare) showed hover tooltips for the wrong category — often offset from the highlighted bar — and jumped as the mouse moved. Vertical charts were fine.

## Why

`chartOptions` set tooltip `mode: "index"` + `intersect: false` without `axis: "y"`. Chart.js index mode defaults to the X axis, so horizontal panels (`indexAxis: "y"`) picked the wrong category. Hover stayed on default `nearest`/`intersect: true`, so highlight and tooltip could disagree.

## What changed

- Added `chartInteraction(indexAxis)` in `dashboard-core.mjs` — returns `{ mode: "index", intersect: false, axis: "y"|"x" }`.
- Wired `options.interaction` from that helper in `dashboard.mjs`; removed tooltip-only `mode`/`intersect` so hover and tooltip share one config.
- Test: `chartInteraction uses Y axis for horizontal bars and X otherwise`.

## Files affected

- `skills/sr-search/src/stockroom/dashboard/static/dashboard-core.mjs`
- `skills/sr-search/src/stockroom/dashboard/static/dashboard.mjs`
- `skills/sr-search/tests-js/dashboard-core.test.mjs`

## Status

- [x] Root cause located
- [x] Failing test written and confirmed
- [x] Fix implemented
- [x] `make test-dashboard-js` green (62/62)
