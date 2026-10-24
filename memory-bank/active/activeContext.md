# Active Context

## Current Task: warehouse-file-growth, milestone 5 (verified newer-format copy)
**Phase:** PREFLIGHT - COMPLETE (PASS WITH ADVISORY)

## What Was Done
- Classified milestone 5 as Level 3 and wrote the plan in `memory-bank/active/tasks.md`
- Preflight returned `FAIL (fixable)`: after `ATTACH`, catalog helpers see both databases
- Revised the plan. Row copy and `EXCEPT ALL` list base tables for the current database only. Schema, constraints, and view columns are read from each file with nothing attached, so `constraint_index` stays in that compare
- Success leaves `warehouse.copy.duckdb` and returns sizes and times. The flock, the check record, and the swap stay in milestone 6

## Next Step
- Operator runs `/niko-build`
