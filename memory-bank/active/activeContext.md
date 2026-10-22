# Active Context

## Current Task: warehouse-file-growth
**Phase:** PLAN - COMPLETE (L4 re-plan: drop the HNSW index)

## What Was Done
- The milestone-1 sub-run (DuckDB 2.0) failed its live shadow run at branch B. Its record is in git at `bd910c3`
- Operator decision (2026-10-21): drop the HNSW index, a two-way door, and strip everything about it except the migration that drops it
- Measured: without `vss` loaded, DuckDB 1.5.4 and 2.0.0 open a file with the index, even with a leftover `.wal` from a killed embed, keep every row, and drop the index inside a transaction. So `vss` leaves the engine too
- Milestone list regenerated (8 milestones): drop the index and `vss`; DuckDB 2.0; new file format; doctor storage report; verified copy; verify-only check; session-start launch; swap kept off
- `projectbrief.md` rewritten for the decision

## Next Step
- Preflight validates the milestone list, then the operator reviews it before `/niko` starts milestone 1
