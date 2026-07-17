# Active Context

## Current Task: dashboard-skill-usage
**Phase:** BUILD - COMPLETE

## What Was Done
- Implemented `stockroom.dashboard.skill_usage` (Claude/Cursor extractors + `EXTRACTORS` registry).
- Added `metrics.skills` + `/api/skills` (`ENDPOINTS["skills"]`) with candidate SQL + server aggregate shape `{skills, invokers, calls}`.
- Client: `"skills"` in `dashboard-data.mjs` ENDPOINTS; three Set A panel builders; markup + `renderChart` wiring after Tool Usage.
- Verification: `make test-dashboard-py` (91), `make test-dashboard-js` (78), full `make test` (575 passed / 4 skipped); ruff format/lint clean.

## Files Created or Modified
- Created: `skill_usage.py`, `test_dashboard_skill_usage.py`
- Modified: `metrics.py`, `dashboard-data.mjs`, `dashboard-core.mjs`, `dashboard.mjs`, `index.html`, JS/static tests

## Deviations from Plan
- None material — nested compare degrades to stacked harness×invoker bar as creative allowed.

## Next Step
- QA review via `/niko-qa` (auto-transition from Level 3 build).
