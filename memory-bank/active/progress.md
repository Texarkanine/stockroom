# Progress

Wire Codecov into stockroom: collect coverage from the engine pytest and dashboard JS test-run roots, upload from CI, decide aggregate vs per-root badge presentation (a16n flags as reference), and add badge(s) to the root README.

**Complexity:** Level 3

## 2026-08-01 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - Confirmed Fresh memory-bank state; persistent context present
    - Clarified and approved intent for Codecov badges + coverage collection + aggregation decision
    - Classified as Level 3
* Decisions made
    - Level 3: multiple CI/tooling components plus an open aggregate-vs-flags design choice (Creative-appropriate); not L4 (no product architecture change)
* Insights
    - Stockroom currently has no Codecov / no `--cov` in CI; README only has REUSE badge
    - a16n uses per-package Codecov Flags + carryforward; root README aggregate badge, package READMEs flag badges
    - Two stockroom test-run roots today: `uv run pytest` (engine) and `make test-dashboard-js` (Node 22)

## 2026-08-01 - CREATIVE (coverage-aggregation) - COMPLETE

* Work completed
    - Explored aggregate-only vs flags vs multi-badge README surfaces
    - Verified Node 22 can emit Codecov-ready `lcov` via `--experimental-test-coverage --test-reporter=lcov`
* Decisions made
    - **B — Flags + aggregate README (a16n-lite):** flagged CI uploads for `engine` and `dashboard-js`; single project aggregate badge on root README; flag badges deferred (easy add later)
* Insights
    - Codecov project badge already aggregates multi-upload commits — flags are for slicing/carryforward, not a prerequisite for aggregation
    - Python LOC will dominate an aggregate %; flags keep JS regressions inspectable without three README badges
