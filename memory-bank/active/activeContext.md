# Active Context

## Current Task: warehouse-file-growth
**Phase:** REVIEW - COMPLETE (advisories folded, swap merged into the check)

## What Was Done
- The milestone-1 sub-run (DuckDB 2.0) failed its live shadow run at branch B. Its record is in git at `bd910c3`
- Operator decision (2026-10-21): drop the HNSW index, a two-way door, and strip everything about it except the migration that drops it. `vss` leaves the engine too
- L4 re-plan, then the twelfth preflight: PASS WITH ADVISORY on 8 milestones
- Operator review (2026-10-22): folded the three advisories, and merged the swap into the check
    - Milestone 1 pins the search shape: nearest chunk per owner, cut to the limit, then join `messages` (153 ms against 1.3 s on the live copy)
    - Milestone 1's leftover-`.wal` test builds the index and kills the writer in separate processes, and asserts `vss` is not loaded
    - Zstd checks read data segments only (`VARCHAR`, `JSON`) and state what an empty table means. This is now an invariant, used by milestones 3, 5, and 6
    - The swap is phase B of the check: rehearse first (`rehearsed`), then at a later session start, at least one day later, copy again, verify, hard-link the backup, and replace. The separate swap milestone is gone, so there are 7 milestones
- `projectbrief.md` updated for the merged check and the zstd segment rule

## Next Step
- `/niko` starts milestone 1: drop the HNSW index and `vss`, on DuckDB 1.5.4, with the migration run on a copy of this machine's warehouse before the first commit that contains it
- The merged 7-milestone list has not been preflighted. The twelfth preflight passed the 8-milestone list; the operator directed these changes at review
