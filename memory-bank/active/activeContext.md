# Active Context

## Current Task: Fortnight backup reclaim and finished-home short-circuit
**Phase:** PLAN - COMPLETE

## What Was Done
- Level 3 plan for task `fortnight-backup-and-quiet-check`. No open questions. Creative decisions stand: check-pass retention at 14 days from `started_at`, and a parent gate that returns only when the backup is not a file.
- Unlink lives in `_acquired` on the `swapped` stop path, under the flock already held. `main` returns before `launch` for version 1 `swapped`, `already-new`, or `mismatch` when that backup is not a file. Importing `stockroom.check` must not import DuckDB.
- `SWAP_BACKUP_FILENAME` moves onto `check` and is re-exported from `doctor`. Hooks stay. Item 2 of issue 155 stays out.

## Next Step
- Preflight the plan.
