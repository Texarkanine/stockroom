# Active Context

## Current Task: dashboard-marathon-link-and-msg-deep-link-investigate
**Phase:** BUILD - COMPLETE

## What Was Done
- Marathon Wrapped: API `session_id`, cell `sessionLink`, `<a class="wrapped-value-link">` with SPA same-tab open.
- Message ordinals: `id="msg-N"`, `#N` indicator link, post-render + hashchange `scrollIntoView({ block: "start" })`.
- Docs: `#msg-{ordinal}` + marathon link note in `docs/user-guide/dashboard.md`.
- Verification: `make test` → 113 JS + 792 pytest passed (2 skipped); ruff check/format clean. Restored cu126 torch after `make lint`'s frozen sync stripped it.

## Files modified
- `/home/mobaxterm/git/stockroom/skills/sr-search/src/stockroom/dashboard/metrics.py`
- `/home/mobaxterm/git/stockroom/skills/sr-search/src/stockroom/dashboard/static/dashboard-core.mjs`
- `/home/mobaxterm/git/stockroom/skills/sr-search/src/stockroom/dashboard/static/dashboard-session.mjs`
- `/home/mobaxterm/git/stockroom/skills/sr-search/src/stockroom/dashboard/static/dashboard.mjs`
- `/home/mobaxterm/git/stockroom/skills/sr-search/src/stockroom/dashboard/static/index.html`
- `/home/mobaxterm/git/stockroom/skills/sr-search/tests/test_dashboard_metrics.py`
- `/home/mobaxterm/git/stockroom/skills/sr-search/tests/test_dashboard_static.py`
- `/home/mobaxterm/git/stockroom/skills/sr-search/tests-js/dashboard-core.test.mjs`
- `/home/mobaxterm/git/stockroom/skills/sr-search/tests-js/dashboard-session.test.mjs`
- `/home/mobaxterm/git/stockroom/docs/user-guide/dashboard.md`

## Next Step
- QA phase.
