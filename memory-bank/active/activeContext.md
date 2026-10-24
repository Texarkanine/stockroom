# Active Context

## Current Task: warehouse-file-growth, milestone 6 (check pass)
**Phase:** BUILD - COMPLETE

## What Was Done
- Added `stockroom.check`: the record, phase choice, readiness ladder, phase A rehearsal, phase B swap, linked resume, and `entry`
- `storage.large_column_zstd_problem` is the shared zstd walk. `_require_zstd` raises `CopyMismatch` with that message
- `doctor.storage_facts` adds one read-only `check` fact on every return. Probe help names the check outcome
- Troubleshooting says how to rename `warehouse.issue147-swap.duckdb` back. The probe index in preparation names the check outcome
- Engine pytest: 1158 passed, 36 skipped. `tests/test_coverage_collection.py` was not run, because that module's `make coverage-engine` sync removes torch. Dashboard JavaScript: 134 passed. Ruff check passed on the edited Python files

## Files
- `skills/sr-search/src/stockroom/check.py` (new)
- `skills/sr-search/src/stockroom/storage.py`
- `skills/sr-search/src/stockroom/doctor.py`
- `skills/sr-search/tests/test_check.py` (new)
- `skills/sr-search/tests/test_doctor.py`
- `skills/sr-search/tests/test_doctor_cli.py`
- `docs/user-guide/troubleshooting/index.md`
- `docs/contributing/preparation.md`

## Decisions
- A backup hash that does not match the hash taken before `os.link` leaves the record `linked`. The replace has already happened, so the next pass writes `swapped` because the inodes differ
- `os.link` and warehouse `os.replace` errors return without writing `linked` or `swapped`. The `started` or `linked` record stays

## Deviations
- Phase B does not write `swapped` on the pass where the backup hash differs from the pre-link hash

## Next Step
- QA review
