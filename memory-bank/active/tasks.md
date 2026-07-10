# Current Task: dashboard-polish

**Complexity:** Level 4

## Preflight findings (2026-07-10)

- **PASS** — milestone list covers #4–#8 with no gaps/overlap; touchpoints match existing dashboard layout (`static/index.html`, `dashboard-data.mjs` / `dashboard-core.mjs`, `metrics.py`, `tests-js/`, `tests/test_dashboard_*.py`).
- **TDD encoding** — deferred to each milestone's sub-run plan (L4 milestone list is decomposition-only; invariant requires test-first + green `make ci` at every boundary).
- **Reuse note for m3** — sessions/wrapped already emit `project_name` via `Path(cwd).name`; extend that rule to `metrics.projects` labels + hover slug metadata rather than inventing a parallel naming path.
- **Advisory** — for m1 date-range UX, prefer a small preset set (e.g. 7d / 30d / 90d / 1y) whose prior-window delta math is unambiguous before investing in free-form calendar + persistence; issue #4 allows this.
