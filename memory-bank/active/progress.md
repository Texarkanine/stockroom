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

## 2026-08-01 - PLAN - COMPLETE

* Work completed
    - Mapped components (pytest-cov, Node lcov, CI, codecov.yml, README, Make, gitignore, docs)
    - TDD plan: `tests/test_coverage_collection.py` for dual-root lcov emit/include
    - Ordered implementation steps (10) + challenges + pre-mortem
* Decisions made
    - Coverage opt-in via Make/CI only — do not put `--cov` in default pytest `addopts`
    - CI: one coverage-enabled run per root (avoid double suite); two flagged codecov uploads
    - Match a16n: `fail_ci_if_error: false`, status checks off initially, carryforward flags
* Insights
    - Node needs no new npm dep for Codecov-ready lcov
    - Stockroom's single README favors aggregate badge; flag badges are a cheap later add

## 2026-08-01 - PREFLIGHT - COMPLETE

* Work completed
    - Validated TDD encoding, conventions, deps, conflicts, completeness
    - Amended plan: stub→red tests→prod→green; CI uses Make coverage targets as SSOT
    - Wrote `.preflight-status` PASS
* Decisions made
    - Collection tests subprocess Make targets (not duplicated argv in workflow)
* Insights
    - No existing coverage/codecov machinery to conflict with
    - Ops dependency: `CODECOV_TOKEN` GitHub secret required before badges leave 404 (outside build; document only)

## 2026-08-01 - BUILD - COMPLETE

* Work completed
    - Dual-root lcov via Make (`coverage-engine` / `coverage-dashboard-js`); collection tests green
    - CI uploads flagged reports; `codecov.yml` + README aggregate badge + contributor docs
    - Full `make test` green (816 pytest / 120 JS); format/lint/lock-check/reuse clean
* Decisions made
    - Coverage stays opt-in (not in pytest `addopts`); CI replaces bare test steps with Make coverage (no double suite)
    - Collection tests subprocess Make with `COVERAGE_PYTEST_ARGS` for a narrow engine case
* Insights
    - Node `--test-coverage-include` cleanly keeps `tests-js` out of SF paths
    - Badge/upload still need ops `CODECOV_TOKEN` before Codecov UI/badge go live

## 2026-08-01 - QA - COMPLETE

* Work completed
    - Reviewed build vs plan/Creative B (KISS/DRY/YAGNI/completeness/regression/integrity/docs)
    - Applied trivial cleanups; wrote `.qa-validation-status` PASS
* Decisions made
    - No substantive plan/design failures — PASS
* Insights
    - Local `make ci` remains coverage-free by design; GitHub CI is where lcov + upload happen
