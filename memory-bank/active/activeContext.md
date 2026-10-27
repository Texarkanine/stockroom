# Active Context

## Current Task: Fortnight backup reclaim and finished-home short-circuit
**Phase:** REFLECT - COMPLETE

## What Was Done
- `_swap_backup_due` is the one predicate. The swapped stop path unlinks `warehouse.issue147-swap.duckdb` when it is true. `check.json` and the live warehouse stay.
- `main` launches a child only for an unfinished version-1 home, or when that predicate is already true. Otherwise it returns without a child and without DuckDB. `OSError` from the parent's stat starts the child. The unlink does not treat that error as due.
- Filenames live on `stockroom.home`. `warehouse` and `doctor` re-export them.
- The user guide says the backup stays 14 days and that a session during those 14 days does not remove it. `docs/architecture/lifecycle.md` says a finished home whose backup is not due starts no child.

## Files
- `skills/sr-search/src/stockroom/check.py`
- `skills/sr-search/src/stockroom/home.py`
- `skills/sr-search/src/stockroom/doctor.py`
- `skills/sr-search/src/stockroom/warehouse.py`
- `skills/sr-search/tests/test_check.py`
- `docs/user-guide/troubleshooting/index.md`
- `docs/architecture/lifecycle.md`

## Deviations
- One predicate, parent `OSError` starts the child, the existing expired-start test carries the fortnight, and one lifecycle sentence. Those were the preflight advisories.
- The user guide says 14 days, the same interval as a fortnight, in the same voice as "one day" in that section.
- Extra tests: a bool `started_at`, a stat error on a due backup, and `--foreground` on a young swap.
- `make test`: 1228 passed, 6 skipped, 2 failed. The failures are not in this change. Dashboard identity resolves `/tmp` to `/private/tmp` on macOS. The root docs lock is stale under `uv lock --locked --refresh`. Dashboard JS: 134 passed, with Node 22 from nvm.

## Reflection
- The revised plan held. The shared predicate raises `OSError`; the parent launches and the unlink does not. Written in `memory-bank/active/reflection/reflection-fortnight-backup-and-quiet-check.md`.
- QA's two notes stay optional: the loose test comment, and the restore steps' writer window.

## Next Step
- Run `/niko-archive` to create the archive document and finalize the current project.
