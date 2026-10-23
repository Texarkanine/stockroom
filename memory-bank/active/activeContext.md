# Active Context

## Current Task: warehouse-file-growth, milestone 4 (doctor storage report)
**Phase:** PLAN - COMPLETE

## What Was Done
- Tag `v3.0.0` is commit `c9fbcc4` on `main`
- `memory-bank/active` is on `warehouse-file-growth`. `constrain-size-as-best-we-can` is unchanged
- Milestone 4 is Level 2. The plan is in `memory-bank/active/tasks.md`
- `stockroom doctor probe` will report file size, block use, a reclaimable estimate from distinct persistent blocks, the storage format, free disk, and `warehouse.issue147-swap.duckdb` when that file exists
- Doctor will not call `home_dir` or `open_current`. The check-record line stays in milestone 6
- Preflight FAIL (fixable) is folded into the plan. Existing probe callers that do not already isolate the home set `STOCKROOM_HOME` to an empty temp home. `live_bytes` unions persistent block ids, drops ids below 0, and skips views. A missing warehouse file is `absent` and is not opened

## Next Step
- Preflight the plan
