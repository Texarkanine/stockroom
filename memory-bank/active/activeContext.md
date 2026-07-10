# Active Context

## Current Task: dashboard-polish-m3-labels-and-help
**Phase:** BUILD - COMPLETE

## What Was Done
- Implemented #8 friendly project labels (`projects` ids + parallel `labels`; unique short-name rule) and sessions/wrapped `project_id`
- Implemented #7 info-icon help on Session Efficiency + First-Prompt Quality only (`PANEL_HELP`, toggle helpers, adapter wiring)
- Chart/session/marathon hover via `labelTitles` / `projectHoverTitle`; `make ci` green (485 passed, 3 skipped; 48 JS)

## Files modified
- `skills/sr-search/src/stockroom/dashboard/metrics.py`
- `skills/sr-search/src/stockroom/dashboard/static/dashboard-core.mjs`
- `skills/sr-search/src/stockroom/dashboard/static/dashboard.mjs`
- `skills/sr-search/src/stockroom/dashboard/static/index.html`
- `skills/sr-search/tests/test_dashboard_metrics.py`
- `skills/sr-search/tests/test_dashboard_static.py`
- `skills/sr-search/tests-js/dashboard-core.test.mjs`

## Deviations from Plan
- Operator amended cwd-disagreement rule before build: full `project_id` when short names are not unique (not most-recent cwd)

## Next Step
- QA review runs next (`/niko-qa`)
