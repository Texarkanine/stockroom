# Current Task: fix-local-dashboard-bounce-noop

**Complexity:** Level 1

## Bug

`make local-dashboard` (and bare `stockroom dashboard` on a matching identity) reported success without restarting. Matching `app_dir`+version short-circuited to no-op while Make unconditionally echoed “dashboard bounced,” so stale in-memory dashboard code kept serving.

## Fix

- Added `--replace` to `stockroom dashboard`: owned listeners are killed and respawned even when identity is current; prints `dashboard: replaced` on stderr when replace completes.
- Bare launch keeps identity-aware no-op.
- `make local-dashboard` passes `--replace`; removed the unconditional “bounced” echo.
- Contributing docs updated to describe force-replace.

## Files

- `skills/sr-search/src/stockroom/dashboard/__main__.py`
- `skills/sr-search/tests/test_dashboard_cli.py`
- `Makefile`
- `docs/contributing/preparation.md`
- `docs/contributing/iteration.md`
