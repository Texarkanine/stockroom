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

