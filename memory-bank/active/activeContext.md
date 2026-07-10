# Active Context

## Current Task: dashboard-polish-m1-top-controls
**Phase:** BUILD - COMPLETE

## What Was Done
- Implemented m1 top controls per plan (TDD steps 1–4) and verified with `make ci`
- Date-range presets wired through core → data → adapter; Aggregate/Compare restyled as segmented pill
- Panel-range labels and overview aria follow selected preset; Wrapped stays unfiltered

## Files Modified
- `skills/sr-search/src/stockroom/dashboard/static/dashboard-data.mjs`
- `skills/sr-search/src/stockroom/dashboard/static/dashboard-core.mjs`
- `skills/sr-search/src/stockroom/dashboard/static/dashboard.mjs`
- `skills/sr-search/src/stockroom/dashboard/static/index.html`
- `skills/sr-search/tests-js/dashboard-data.test.mjs`
- `skills/sr-search/tests-js/dashboard-core.test.mjs`
- `skills/sr-search/tests/test_dashboard_static.py`

## Decisions During Build
- State shape extended with `dateRange` + `window`; `daterange` action → `refetch`
- Shared `.segmented` class for both date-range and mode fieldsets
- Adapter only wires DOM; bounds/labels live in tested core/data modules

## Deviations from Plan
- None — built to plan

## Verification
- `make test-js`: 38 passed
- Targeted dashboard pytest: 15 passed
- `make ci`: ruff + 38 JS + 479 pytest (3 skipped) + reuse lint — all green

## Next Step
- QA review runs automatically (`/niko-qa`)
