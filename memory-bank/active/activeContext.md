# Active Context

## Current Task: warehouse-file-growth, milestone 6 (check pass)
**Phase:** REFLECT - COMPLETE

## What Was Done
- Added `stockroom.check`: the record, phase choice, readiness ladder, phase A rehearsal, phase B swap, linked resume, and `entry`
- `storage.large_column_zstd_problem` is the shared zstd walk. `_require_zstd` raises `CopyMismatch` with that message
- `doctor.storage_facts` adds one read-only `check` fact on every return. Probe help names the check outcome
- Troubleshooting says how to rename `warehouse.issue147-swap.duckdb` back. The probe index in preparation names the check outcome
- QA passed. Two advisories stayed advisories
- Reflected in `memory-bank/active/reflection/reflection-warehouse-file-growth-m6.md`

## Decisions
- A backup hash that does not match the hash taken before `os.link` leaves the record `linked`. The next pass writes `swapped` because the inodes differ
- The crash after `os.link` and before a durable `linked` record stays unhandled. An expired `started` entry does not replace the warehouse

## Next Step
- Run `/niko` to continue to the next milestone.
