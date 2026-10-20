# Progress

Stop the warehouse file growing far past the history it holds, as specified in [issue 147](https://github.com/Texarkanine/stockroom/issues/147) and `memory-bank/active/projectbrief.md`. Keep HNSW, rebuild it around embedding writes, insert vectors through NumPy, create new warehouses in the current DuckDB storage format with ZSTD text columns, rewrite an existing warehouse once in verify-only mode, and teach read-only `stockroom doctor` to report the file. The swap that replaces the live file stays a separate change and stays off.

**Complexity:** Level 4

## 2026-10-20 - COMPLEXITY ANALYSIS - COMPLETE

* Work completed
    - Confirmed the issue is the spec, including the safety rules and the verify-only first release
    - Classified the work as Level 4
* Decisions made
    - Level 4 because the change crosses warehouse creation, embed writes, index lifetime, an automatic rewrite, and doctor, and a bad rewrite can lose the warehouse
    - Issue 147 supersedes the earlier creative note that dropped HNSW and added a `compact` command
* Insights
    - The approach is already decided in the issue. Planning only has to split it into milestones that can ship on their own

## 2026-10-20 - PLAN - COMPLETE

* Work completed
    - Split the issue into seven milestones in dependency order
    - Recorded the cross-milestone invariants, including verify-only as the default writer path
* Decisions made
    - New-file format and ZSTD: Level 2. One creation path, two column clauses, and one doc page
    - NumPy inserts: Level 2. One insert path in the embed writer
    - HNSW drop and recreate: Level 3. The growth bound, the skip-when-idle rule, and semantic search still answering
    - Doctor storage report: Level 2. Read-only facts on the existing probe
    - Verified copy: Level 3. Equality, catalog, HNSW, and every schema fixture, with the original untouched
    - Verify-only writer path: Level 3. Flock, skip rules, cleanup, and faults before any swap
    - Hard-link swap kept off: Level 3. The proof from the issue, without turning the default path into a replace
* Insights
    - Format, NumPy inserts, and the doctor report can start together. The HNSW wrap waits on the insert path. The copy waits on the new-file format. The swap waits on verify-only and on the doctor backup name

## 2026-10-20 - PREFLIGHT - COMPLETE

* Work completed
    - Validated Level 4 milestone decomposition in `memory-bank/active/milestones.md` against `projectbrief.md`
    - Confirmed serial-safety, DAG alignment, coverage, invariant constraints, and definitions of done across all 7 milestones
    - Recorded preflight status: PASS WITH ADVISORY
* Decisions made
    - Preflight result is PASS WITH ADVISORY. The milestone list was not changed
    - Advisory, not adopted: a verification receipt so verify-only mode does not rebuild on every later writer open, and so doctor can show that a copy already verified
* Insights
    - The 7-milestone decomposition cleanly separates read-only diagnostic visibility, incremental vector insert performance, index rebuild bounds, and non-destructive shadow verification from the final inactive swap operation

