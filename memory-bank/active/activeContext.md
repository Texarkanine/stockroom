# Active Context

**Current Task:** codecov-readme-badges
**Phase:** BUILD - COMPLETE
**Complexity:** Level 3 (canonical in `progress.md`)

## What Was Done

- TDD: `tests/test_coverage_collection.py` subprocesses root Make coverage targets (4 green)
- `pytest-cov` + `[tool.coverage.*]` (opt-in; not in default `addopts`); lock regenerated
- Make: `coverage-engine`, `coverage-dashboard-js`, `coverage`; `test` / `test-dashboard-js` unchanged
- `codecov.yml`: flags `engine` / `dashboard-js` + carryforward; project/patch status off
- CI: Make coverage SSOT + two `codecov-action@v7` uploads (`fail_ci_if_error: false`)
- gitignore coverage artifacts; README aggregate Codecov badge; iteration docs updated
- Verification: ruff format/lint, lock-check, reuse lint clean; `make test` → 816 pytest + 120 JS passed (4 skipped)

## Deviations from Plan

None — built to plan (Creative B).

## Next Step

QA review runs next (`/niko-qa` / L3 autonomous transition).
