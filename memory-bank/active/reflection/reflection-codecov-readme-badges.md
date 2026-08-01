---
task_id: codecov-readme-badges
date: 2026-08-01
complexity_level: 3
---

# Reflection: codecov-readme-badges

## Summary

Wired dual-root Codecov collection (engine pytest-cov + dashboard Node lcov), flagged CI uploads, and a single aggregate README badge (Creative B / a16n-lite). Build and QA passed; live badges still depend on ops `CODECOV_TOKEN`.

## Requirements vs Outcome

Delivered: both test-run roots collect Codecov-ready lcov; CI uploads with `engine` / `dashboard-js` flags; aggregate README badge; local Make SSOT; contributor docs. No requirements dropped. Flag badges on README deferred by design (Creative B).

## Plan Accuracy

The ordered plan held: TDD collection tests → pytest-cov/Make → codecov.yml/CI/gitignore/README/docs. Preflight amendments (stub→red→green; CI/Make SSOT; `COVERAGE_PYTEST_ARGS`) were the right shape and avoided double suite cost. No surprise dependencies beyond expected lock churn for `pytest-cov`.

## Creative Phase Review

**B — Flags + aggregate README** translated cleanly: two upload steps, one badge URL, carryforward flags, status checks off. No friction implementing flag paths vs README surface. The "Python LOC will dominate aggregate %" tradeoff remains accepted and untested in production until token + first upload.

## Build & QA Observations

Build was straightforward once Make targets existed; collection tests went red→green as designed. Node `--test-coverage-include` behaved as researched. QA only found trivial debris (unused helper kwarg, redundant gitignore paths, stale `make ci` help) — no plan/design gaps.

## Cross-Phase Analysis

Creative research (Node lcov works; Codecov aggregates multi-flag commits) prevented a wrong exclusive "aggregate vs flags" fork. Preflight's Make-SSOT amendment kept tests, CI, and local invocation aligned and was the highest-leverage process catch. Ops `CODECOV_TOKEN` remains outside the repo lifecycle — correctly documented, not fake-solved in code.

## Insights

### Technical
- Prefer subprocessing root Make coverage targets in tests when CI will call those same targets — one argv surface, no workflow/test drift.
- Keep `--cov` out of default pytest `addopts` when coverage is a CI/reporting concern; opt-in Make targets preserve fast local `make test`.

### Process
- For CI/tooling tasks with an aggregation UX choice, a short Creative pass (flags vs badges) is cheaper than baking README surface into the first plan draft.
