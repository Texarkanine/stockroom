# Active Context

## Current Task: Fortnight backup reclaim and finished-home short-circuit
**Phase:** PLAN - COMPLETE

## What Was Done
- Revised the Level 3 plan to the operator's gate from 2026-10-27. The hook text stays.
- `main` calls `launch()` in two cases: the home is not a finished version-1 record, or version 1 `swapped` has a backup file, a numeric `started_at`, a fortnight elapsed, a live warehouse file, and a different inode.
- `main` returns without a child, and without DuckDB, when that child would leave the disk alone. A young swapped backup is one of those returns. `already-new` and `mismatch` return even if a backup file is present. The parent does not unlink.
- The two filenames the parent stats move to `stockroom.home`. `warehouse` and `doctor` re-export them.

## Next Step
- Preflight the revised plan.
