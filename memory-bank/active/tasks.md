# Task: release-quality-docs

* Task ID: release-quality-docs
* Complexity: Level 2
* Type: documentation content draft (search + dashboard pages)

Draft `docs/user-guide/search.md` and `docs/user-guide/dashboard.md` to finished user-guide quality.

## Test Plan (TDD)

Docs-only — Verification Plan is the gate (TDD N/A for code):

1. Acceptance sweep B1–B6 before claiming complete.
2. `make docs-build` (`properdocs build --strict`).

### Behaviors to Verify

- **B1 Search default**: ✅
- **B2 Three skills**: ✅
- **B3 Dashboard overview**: ✅
- **B4 Screenshots**: ✅ top + convo views
- **B5 DRY**: ✅ using-skills + quickstart pointers
- **B6 Build**: ✅ `make docs-build` PASS; reuse PASS

### Edge cases

- **E1** Skipped duckdb CLI shot ✅
- **E2** using-skills left out of nav; slimmed in place ✅

## Implementation Plan

1. **Draft search.md** ✅
2. **Draft dashboard.md** ✅
3. **DRY using-skills** ✅ (+ quickstart links)
4. **Verify** ✅

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Pre-Mortem complete
- [x] Preflight
- [x] Build
- [x] QA
