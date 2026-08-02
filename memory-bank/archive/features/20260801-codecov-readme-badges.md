---
task_id: codecov-readme-badges
complexity_level: 3
date: 2026-08-01
status: completed
---

# TASK ARCHIVE: Codecov README Badges

## SUMMARY

Wired dual-root Codecov coverage into stockroom: engine pytest-cov and dashboard Node 22 lcov collection via Make SSOT targets, flagged CI uploads (`engine` / `dashboard-js`), `codecov.yml` with carryforward and status checks off, and a single aggregate Codecov badge on the root README (Creative B / a16n-lite). Contributor docs note Make targets and the ops `CODECOV_TOKEN` secret. Shipped on `collect-coverage` via draft [PR #116](https://github.com/Texarkanine/stockroom/pull/116); post-reflect review fixed an xdist race with parallel-safe `COVERAGE_*_DIR` + `tmp_path`.

## REQUIREMENTS

From the project brief:

1. Collect coverage from stockroom's test-run roots (engine pytest under `skills/sr-search/`, dashboard JS via Node 22 / `make test-dashboard-js`).
2. Upload coverage to Codecov from CI.
3. Decide aggregate vs per-root presentation (a16n flags as reference).
4. Add the chosen Codecov badge(s) to the root README beside REUSE.
5. Wire local Make/docs so contributors can generate coverage the same way CI does.

Constraints: no third test framework; prefer a16n patterns; do not break `make test` / CI green; product runtime out of scope.

Acceptance: CI produces Codecov-ready artifacts and uploads; README badge matches aggregation policy (404 until first successful upload + token is expected); decision recorded in `codecov.yml` / badge URL; existing tests stay green with coverage collection enabled.

## CREATIVE PHASE DECISIONS

**Design question:** How should stockroom structure Codecov *uploads* and README *badges* given two test-run roots?

**Options evaluated:**

- **A — Aggregate-only:** Combined/unflagged upload; single README badge; no flags.
- **B — Flags + aggregate README (a16n-lite):** Two flagged uploads; root README shows default project aggregate only; per-root detail in Codecov UI / optional later `?flag=` badges.
- **C — Flags + two README badges only:** Flagged uploads; engine and dashboard-js badges, no aggregate.
- **D — Flags + aggregate and two flag badges on README:** Full a16n surface on one README.

**Selected: B.** Codecov's default project badge already aggregates multi-upload commits; flags keep roots separable for carryforward and inspection without three README badges. Stockroom has a single root README (unlike a16n's per-package READMEs), so B matches a16n's root surface without inventing package README homes. Skipping flags (A) is hard to reverse; adding flag badges to B is a one-line README change.

**Tradeoff accepted:** README does not show engine vs dashboard percentages at a glance — that lives in Codecov (or later `?flag=` badges). Python LOC will dominate aggregate %; flags mitigate masking for inspection.

**Friction in implementation:** None on the Creative choice itself. Node `--experimental-test-coverage` + `lcov` reporter worked as researched; post-reflect PR review surfaced an xdist race on shared `coverage-js/` output (fixed with per-test dirs, not by abandoning B).

## IMPLEMENTATION

**Coverage collection (Make SSOT):**

- `coverage-engine` — pytest with `pytest-cov`, emits `skills/sr-search/coverage/lcov.info` (source=`stockroom`; omit tests/vendored); `--cov` stays out of default pytest `addopts`.
- `coverage-dashboard-js` — Node 22 `--experimental-test-coverage` + `lcov` reporter into `coverage-js/lcov.info`, scoped with `--test-coverage-include` to `src/stockroom/dashboard/static/**`.
- `coverage` depends on both; `make test` / `test-dashboard-js` remain coverage-free for local speed.
- Knobs: `COVERAGE_PYTEST_ARGS` (narrow engine runs for tests); later `COVERAGE_ENGINE_DIR` / `COVERAGE_JS_DIR` for parallel-safe collection tests.

**Codecov / CI / docs:**

- Root `codecov.yml` — flags `engine` and `dashboard-js` with paths + `carryforward: true`; project/patch status `enabled: false` initially; filename stays `codecov.yml` (Codecov documents that name, not `codecov.yaml`).
- `.github/workflows/ci.yaml` — replaces bare pytest/JS steps with root Make coverage targets; two `codecov/codecov-action@v7` uploads with flags, `fail_ci_if_error: false`, `CODECOV_TOKEN`.
- README — one aggregate badge URL for `Texarkanine/stockroom` beside REUSE.
- `.gitignore` — coverage artifacts (`.coverage`, `coverage/`, `coverage-js/`, `htmlcov/`).
- Contributor docs — `docs/contributing/iteration/engine.md` and `dashboard.md` document Make targets and token/badge-404 expectations.

**Key files:** `skills/sr-search/pyproject.toml` + lock (`pytest-cov`), `Makefile`, `codecov.yml`, `.github/workflows/ci.yaml`, `README.md`, `.gitignore`, `skills/sr-search/tests/test_coverage_collection.py`, iteration docs.

**PR #116 feedback:** Dismissed CodeRabbit `fetch-depth` and Node-22 Make DRY nits; fixed coverage-js xdist race via parallel-safe output dirs + `tmp_path` (pushed `a1bf309`). Operator note: badge is satisfied by main-branch uploads; PR uploads remain wired as optional extras.

## TESTING

- TDD: stub → red → green for `tests/test_coverage_collection.py` — engine/JS lcov emit, JS include scope (static SF paths; tests-js not dominant), `make test-dashboard-js` unchanged semantics. Collection tests subprocess root Make targets (SSOT with CI).
- Preflight PASS (amended: stub→red→green; CI uses Make; `COVERAGE_PYTEST_ARGS`).
- Build verification: full suite green (816 pytest / 120 JS at build checkpoint); format/lint/lock-check/reuse clean.
- `/niko-qa` PASS — trivial cleanups only (unused helper kwarg, redundant gitignore, stale `make ci` help); no plan/design gaps.
- Post-reflect: xdist-green collection suite after `COVERAGE_*_DIR` isolation.

## LESSONS LEARNED

- Prefer subprocessing root Make coverage targets in tests when CI will call those same targets — one argv surface, no workflow/test drift.
- Keep `--cov` out of default pytest `addopts` when coverage is a CI/reporting concern; opt-in Make targets preserve fast local `make test`.
- Aggregation is not either/or with flags: Codecov aggregates for the project badge *and* can flag uploads; the real choice is README surface and whether CI tags roots.
- Shared fixed coverage output directories race under xdist; Make knobs for per-test dirs beat serialize/locks for a small plumbing suite.
- Ops `CODECOV_TOKEN` stays outside the repo lifecycle — document, don't fake-solve in code; badge 404 until first upload is expected.

## PROCESS IMPROVEMENTS

- For CI/tooling tasks with an aggregation UX choice, a short Creative pass (flags vs badges) is cheaper than baking README surface into the first plan draft.
- Preflight's Make-SSOT amendment was the highest-leverage process catch — kept tests, CI, and local invocation aligned and avoided double suite cost.

## TECHNICAL IMPROVEMENTS

- Optional later: add `?flag=engine` / `?flag=dashboard-js` badges to README without redoing CI.
- Local `make ci` remains coverage-free by design; GitHub CI is where lcov + upload happen — intentional split, not a gap to "fix" by slowing every local CI.

## NEXT STEPS

- Set GitHub Actions secret `CODECOV_TOKEN` so uploads succeed and the README badge leaves 404.
- Mark [PR #116](https://github.com/Texarkanine/stockroom/pull/116) ready and merge when satisfied.
- Optionally revisit whether PR-branch uploads are worth keeping once main uploads alone satisfy the badge.
