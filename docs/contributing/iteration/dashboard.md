# Dashboard

Product behavior and URL: [Dashboard](../../user-guide/dashboard.md) (default [http://localhost:58008](http://localhost:58008/)).

| Layer | Path |
| --- | --- |
| Front-end | `skills/sr-search/src/stockroom/dashboard/static/` — native ES modules, vendored Chart.js + markdown-it, no bundler / no npm install |
| JS tests | `skills/sr-search/tests-js/*.test.mjs` |
| Server | `skills/sr-search/src/stockroom/dashboard/` |
| CLI | `skills/sr-search/src/stockroom/dashboard/__main__.py` |
| Python tests | `skills/sr-search/tests/test_dashboard_*.py` |

## Development Loop

Static ESM is read from disk on each request; Python changes only get picked up after the dashboard server process is replaced.

1. Edit server/metrics (and any other Python under `dashboard/`) plus the static modules that consume the API.
2. Bounce so this checkout's Python is what is listening:

	```bash
	make local-dashboard
	```

3. Hard-refresh the browser so cached ESM is not stale.
4. Run the dashboard contract gates:

	```bash
	make test-dashboard-js
	make test-dashboard-py
	```

## Relevant Make targets

| Target | Role |
| --- | --- |
| `test-dashboard-js` | Dashboard ES-module tests (`node --test`; Node 22; no sync) |
| `test-dashboard-py` | `tests/test_dashboard_*.py` only (torch-safe; no sync) |
| `test` | Full pytest (xdist `-n auto`) + JS (runs `sync` first — strips torch) |
| `local-dashboard` | Force-replace `stockroom dashboard` for this checkout (`--replace`) |
