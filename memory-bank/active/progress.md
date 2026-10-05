# Progress

Add optional `--harness` and `--role` scopes to `stockroom semantic` so ranking happens inside that filtered set, teach the two skills, then reflect and open a non-draft pull request.

**Complexity:** Level 2

## 2026-10-05 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - Confirmed intent against the creative decision
    - Classified the work as Level 2
    - Wrote the project brief, active context, and task stub
* Decisions made
    - Level 2, not Level 3: one command, design already chosen, no new subsystem
    - The creative document stays the design; plan does not reopen it
* Insights
    - DuckDB 1.5.4 VSS post-filters a `WHERE` on the HNSW limit query, so the scoped path must rank the joined set

## 2026-10-05 - PLAN - COMPLETE

* Work completed
    - Wrote the Level 2 plan in `memory-bank/active/tasks.md`
    - Mapped behaviors onto the existing `test_semantic.py`
    - Split executable ranking and CLI work from prose skill and doc updates
* Decisions made
    - Unfiltered search stays on HNSW; a scope ranks the joined set
    - One starvation test is required because a tiny fixture will not catch post-filter
    - Human docs get a short mention, not a second flag table
* Insights
    - Identical `FakeEncoder` text is distance 0, which is enough for the small scope tests

## 2026-10-05 - PREFLIGHT - PASS WITH ADVISORY

* Work completed
    - Preflight passed with an advisory on scoped dedup
* Decisions made
    - Build may rank and max-sim the joined set in one SQL statement instead of a second messages lookup
* Insights
    - `OVERFETCH` does not belong on the scoped path, because that path is an exact rank of the filtered rows

## 2026-10-05 - BUILD - COMPLETE

* Work completed
    - Added `--harness` and `--role` and the joined scoped rank
    - Covered the nearer-outsider starvation case with 32 chunks
    - Updated the two skills, the human docs, and the system pattern
    - `make lint` passed. `make test` was 880 passed, 4 skipped, plus 134 dashboard JS tests
* Decisions made
    - Scoped max-sim is a `QUALIFY` over the join, from the preflight advisory
    - Left `uv.lock` alone. The hermetic lock test fails on uv 0.8.22 and passes on uv 0.12.22
* Insights
    - Thirty-two nearer 384-d outsiders are enough for a post-filtered HNSW limit to miss the in-scope row

## 2026-10-05 - PREFLIGHT - COMPLETE (PASS WITH ADVISORY)

* Work completed
    - Validated implementation plan against codebase reality, conventions, and dependencies
    - Confirmed strict TDD encoding for all executable units (test stubs and red runs precede production code)
    - Formulated advisory recommendation for single-pass window deduplication on the scoped join path
* Decisions made
    - Plan accepted with advisory; ready for build phase

## 2026-10-05 - QA - COMPLETE (PASS)

* Work completed
    - Reviewed the build diff against the plan, creative decision, and brief; re-ran `tests/test_semantic.py` (33 passed, 1 skipped)
    - Wrote `memory-bank/active/.qa-validation-status`
* Decisions made
    - PASS with no blocking findings; no build or plan rework required
* Insights
    - Scoped dedup landed as one SQL statement per the preflight advisory; unfiltered HNSW path is unchanged

## 2026-10-05 - REFLECT - COMPLETE

* Work completed
    - Wrote `memory-bank/active/reflection/reflection-semantic-cli-filters.md`
    - Left `productContext.md` and `techContext.md` unchanged
* Decisions made
    - The two-path search is the design to keep, not a filter-aware index
* Insights
    - A small fixture cannot prove a scope survived HNSW post-filtering. Thirty-two nearer outsiders can

## 2026-10-05 - REWORK PLAN - COMPLETE

* Work completed
    - Recorded review 5420273503 as a rework on the project brief
    - Planned removal of the flag listings from the CLI Role cell, the search page, and the skill index
* Decisions made
    - The flag home is `skills/sr-semantic/SKILL.md`. No new section
    - `sr-search` keeps its route row. Architecture keeps the two-path sentence
    - No engine or test change
* Insights
    - The Role column is the subcommand's job. Speaker `--role` does not belong in that cell

## 2026-10-05 - PREFLIGHT - COMPLETE (PASS WITH ADVISORY)

* Work completed
    - Verified all three target files against the plan's exact quoted text — byte-for-byte match
    - Grepped `docs/` and `skills/` repo-wide for `--harness`/`--role` to confirm no missed touchpoint
    - Confirmed all four units are correctly classified as prose/policy; no TDD gap
* Decisions made
    - Plan accepted as-is; ready for build phase
* Insights
    - The four-location drift behind the review comment is structural (no single generator owns the flag fact); recorded as a non-blocking advisory for a future doc-gen chokepoint, not a change to this plan

## 2026-10-05 - BUILD - COMPLETE

* Work completed
    - Removed the flag listings from `docs/advanced/cli.md`, `docs/user-guide/search.md`, and `docs/user-guide/skills.md`
    - Left the skill flag home, the `sr-search` route row, and the architecture two-path sentence in place
    - `make lint` passed. `make docs-build` passed. Dashboard JS tests: 134 passed. Pytest: 881 passed, 4 skipped, 1 failed
* Decisions made
    - The pytest failure is `test_docs_lock_is_not_stale` on uv 0.8.22. The lock stays as committed for uv 0.12.22
* Insights
    - `make ci` stops at the same root lock check before tests. Lint and the suite were run directly

## 2026-10-05 - QA - COMPLETE (PASS)

* Work completed
    - Reviewed the rework diff against the plan: three doc files only, no engine or test change
    - Grepped `docs/`, `skills/`, and `memory-bank/systemPatterns.md` for stray flag listings; found none outside the flag home and the retained route row
    - Wrote `memory-bank/active/.qa-validation-status`
* Decisions made
    - PASS with no blocking findings; no build or plan rework required
* Insights
    - The untracked `.cursor/skills/stockroom-local/` directory is unrelated to this task
