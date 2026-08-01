# Decision: Coverage Aggregation vs Per-Root Presentation

## Context

**What:** How stockroom should structure Codecov *uploads* and README *badges* given two test-run roots — engine pytest (`skills/sr-search`) and dashboard JS (`node --test` on `tests-js/`).

**Why it matters:** Locks CI upload shape, `codecov.yml` flags, badge URL(s), and whether JS coverage is first-class alongside Python. Wrong choice either hides a language-specific regression behind the other root's LOC weight, or clutters the README / overbuilds for a two-root repo.

**Constraints:**
- Collect from both roots (neither scoped out)
- Prefer a16n patterns (Flags, carryforward, `codecov-action`) unless simpler is clearly enough
- Preserve green `make test` / CI; coverage is additive
- No third test framework — extend pytest + Node 22 built-in runner
- Product runtime out of scope

**Fact from research:** Codecov's default project badge aggregates all coverage uploaded for a commit (across files/flags). Flags slice that same data for per-root badges, PR status, and carryforward. a16n uses both: root README = aggregate badge; package READMEs = `?flag=` badges. Node 22 can emit `lcov` via `--experimental-test-coverage --test-reporter=lcov` (verified locally); Python needs `pytest-cov` (not yet a dep).

## Options Evaluated

- **A — Aggregate-only:** One combined upload (or unflagged dual upload), single README badge; no flags
- **B — Flags + aggregate README (a16n-lite):** Two flagged uploads (`engine`, `dashboard-js`); root README shows default project aggregate badge only; per-root detail lives in Codecov UI / optional PR comment
- **C — Flags + two README badges only:** Flagged uploads; README shows engine and dashboard-js badges, no aggregate
- **D — Flags + aggregate and two flag badges on README:** Full a16n surface collapsed onto one README

## Analysis

| Criterion | A Aggregate-only | B Flags + aggregate README | C Two flag badges | D Aggregate + two flags on README |
| --- | --- | --- | --- | --- |
| Matches "does Codecov aggregate?" | Yes | Yes (default badge) | No (hides aggregate) | Yes |
| Per-root visibility | Poor (LOC-weighted merge only) | Codecov UI / flags; not on README | Excellent on README | Excellent on README |
| Consistency with a16n | Partial | Closest (root surface) | Partial | Closest (if we had package READMEs) |
| Simplicity | Highest | High | Medium | Lowest (three badges) |
| Reversibility | Easy to add flags later | Easy to add flag badges later | Easy to add aggregate later | Easy to remove badges |
| Masking risk (Py ≫ JS LOC) | High | Mitigated in Codecov | Mitigated on README | Mitigated |

Key insights:
- Aggregation is not an either/or with flags: Codecov aggregates for the project badge *and* can flag uploads. The real choice is README surface and whether CI tags roots.
- Stockroom has a single root README (unlike a16n's per-package READMEs), so putting three badges on it (D) is noisier than a16n's split.
- Skipping flags (A) is hard to reverse once PR history is unflagged mush; adding flag badges to a B setup is a one-line README change.
- JS coverage needs no new npm dep — Node's lcov reporter works; keep `make test` printing human-readable results (multiple `--test-reporter` or keep coverage opt-in on a dedicated target).

## Decision

**Selected**: B — Flags + aggregate README (a16n-lite)

**Rationale**: Answers the operator's "will Codecov aggregate them?" with yes for the default project badge, while using Flags so the two roots stay separable in Codecov (and for carryforward when only one root's tests run). Matches a16n's root README surface without inventing per-package README homes stockroom does not have. Simpler than D; more future-proof than A.

**Tradeoff**: README does not show engine vs dashboard percentages at a glance — that lives one click into Codecov (or can be added later as `?flag=` badges without changing CI).

## Implementation Notes

- Add `pytest-cov` to engine `dev` dependency group; CI/Make coverage path emits `coverage/lcov.info` (or xml) under `skills/sr-search/` for the Python tree (`src/stockroom/`).
- Dashboard JS: `mkdir -p coverage-js` (or similar) and `node --experimental-test-coverage --test-reporter=lcov --test-reporter-destination=… --test tests-js/*.test.mjs`, scoped with `--test-coverage-include` to `src/stockroom/dashboard/static/**` so test files don't dominate.
- CI: after both runs, two `codecov/codecov-action` uploads with `flags: engine` and `flags: dashboard-js`, `token: ${{ secrets.CODECOV_TOKEN }}`, `fail_ci_if_error: false` (match a16n until token is proven).
- `codecov.yml`: define `engine` and `dashboard-js` flags with `paths` + `carryforward: true`; keep project/patch status disabled initially (a16n pattern) unless we want gates later.
- Root README: one badge — `[![codecov](https://codecov.io/github/Texarkanine/stockroom/graph/badge.svg)](https://codecov.io/github/Texarkanine/stockroom)` beside REUSE.
- Document `CODECOV_TOKEN` secret setup and "badge 404 until first upload" in contributor iteration docs if we touch them.
- Optional later: add `?flag=engine` / `?flag=dashboard-js` badges to README without redoing CI.
