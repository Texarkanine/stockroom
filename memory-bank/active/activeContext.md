# Active Context

## Current Task: dashboard-token-usage
**Phase:** BUILD - COMPLETE

## What Was Done
- Exposed `tokens` (and detail `model`) from `session_token_usage` via `_tokens_payload`
- Added reusable `dashboard-tokens.mjs` (`formatTokenCompact`, `mountTokenDisplay`) used by list rows and detail meta
- Tokens column between Messages and Model; detail shows Model + Tokens (no Session label)
- Docs updated in `docs/user-guide/dashboard.md`
- Verification: dashboard py/js, lint, format-check, full `make test` green

## Files modified
- `skills/sr-search/src/stockroom/dashboard/metrics.py`
- `skills/sr-search/src/stockroom/dashboard/static/dashboard-tokens.mjs` (new)
- `skills/sr-search/src/stockroom/dashboard/static/dashboard-session.mjs`
- `skills/sr-search/src/stockroom/dashboard/static/dashboard.mjs`
- `skills/sr-search/src/stockroom/dashboard/static/index.html`
- `skills/sr-search/tests/test_dashboard_metrics.py`
- `skills/sr-search/tests/test_dashboard_static.py`
- `skills/sr-search/tests-js/dashboard-tokens.test.mjs` (new)
- `skills/sr-search/tests-js/dashboard-session.test.mjs`
- `docs/user-guide/dashboard.md`

## Next Step
- QA phase (automatic for Level 2)
