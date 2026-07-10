# Active Context

## Current Task: dashboard-lifecycle-after-plugin-move
**Phase:** BUILD - COMPLETE

## What Was Done
- Added `dashboard/identity.py` — port-scoped durable identity under stockroom home
- Extended `dashboard/__main__.py` — reuse / replace / leave-foreign decision matrix; foreground writes identity on bind
- Tests: `test_dashboard_identity.py` (5) + extended `test_dashboard_cli.py` (11); full suite 467 passed, 3 skipped
- Documented machine-scoped replace behavior in `docs/using.md`

## Files modified
- `skills/sr-search/src/stockroom/dashboard/identity.py` (new)
- `skills/sr-search/src/stockroom/dashboard/__main__.py`
- `skills/sr-search/tests/test_dashboard_identity.py` (new)
- `skills/sr-search/tests/test_dashboard_cli.py`
- `docs/using.md`

## Deviations
- Combined units 2–3 in one launcher pass (foreground write landed with decision matrix); tests still written/extended first for each behavior

## Next Step
- QA semantic review (autonomous for L2)
