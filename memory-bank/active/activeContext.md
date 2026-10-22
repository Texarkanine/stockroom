# Active Context

## Current Task: warehouse-file-growth, milestone 2 (DuckDB 2.0)
**Phase:** PLAN - COMPLETE

## What Was Done
- Milestone 1 is checked off; milestone 2 is classified Level 3
- Wrote the Level 3 plan in `tasks.md`: 7 steps (scope the Hub filter, finish the shadow script, clone-recipe smoke, two pre-lock gates, the one-commit 2.0 move, live checks, final verification) and 11 behaviours (N1 to N5, S1 to S6)
- Found the nanobind cause by measurement: stockroom's own `_DropUnauthenticatedHubWarning` stays on the `huggingface_hub` logger for the process, which keeps `stockroom.embed` and so `duckdb` alive past nanobind's shutdown check. Removing it after the model loads silences `embed` and `semantic` under 2.0.0
- Measured: full suite green on a 2.0.0 overlay (1,040 passed, 38 skipped); the lock resolves with only duckdb changing; 2.0.0 wheels cover every platform; `warehouse.open()` on 2.0.0 makes a `v2.0.0+` file

## Next Step
- Preflight (subagent), then the operator runs `/niko-build`
