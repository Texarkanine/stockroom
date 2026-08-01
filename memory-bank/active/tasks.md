# Task: codecov-readme-badges

* Task ID: codecov-readme-badges
* Complexity: Level 3
* Type: feature (CI/tooling)

Wire Codecov into stockroom: collect coverage from test-run roots, upload from CI, present badge(s) on the README. a16n is the multi-root reference.

## Component Analysis

### Affected Components
- **Engine pytest / uv project** (`skills/sr-search/`): runs Python tests today without coverage → add pytest-cov (or equivalent), emit Codecov-friendly report (lcov/xml)
- **Dashboard JS tests** (`skills/sr-search/tests-js/`, `make test-dashboard-js`): Node 22 `node --test` today without coverage → enable Node experimental coverage / reporter that Codecov accepts
- **CI** (`.github/workflows/ci.yaml`): single `engine` job runs pytest + JS → collect + upload to Codecov
- **Codecov config** (`codecov.yml` at repo root, new): flags / status / comment policy
- **README** (root): add Codecov badge(s) next to REUSE
- **Makefile / contributor docs** (possible): local `coverage` targets matching CI

### Cross-Module Dependencies
- CI orchestrates both test roots and uploads reports Codecov merges by commit SHA
- Badge URLs depend on flag/aggregation policy chosen in Creative
- Local Make targets should mirror CI collection commands so contributors see the same numbers

### Boundary Changes
- No product/runtime API changes
- Dev dependency + pytest/Make/CI command surface changes only
- GitHub secret `CODECOV_TOKEN` required (ops, outside repo)

### Invariants & Constraints
- Must preserve existing green `make test` / CI path (coverage is additive, not a separate incompatible runner)
- Must not invent a third test framework
- Prefer a16n patterns (Flags, carryforward, codecov-action) unless two-root shape clearly wants simpler
- Product runtime out of scope

## Open Questions

- [x] OQ1: Coverage aggregation vs per-root presentation → Resolved: **Flags + aggregate README (a16n-lite)** — two flagged uploads (`engine`, `dashboard-js`); root README shows default project aggregate badge only (see `memory-bank/active/creative/creative-coverage-aggregation.md`)
