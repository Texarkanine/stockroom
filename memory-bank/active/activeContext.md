# Active Context

## Current Task: warehouse-file-growth, milestone 3 (new file format)
**Phase:** PREFLIGHT - COMPLETE (PASS WITH ADVISORY)

## What Was Done
- Milestone 2 checked off; its sub-run files cleared. Milestone 3 classified Level 3
- After the classification commit, the commit hook stripped torch from the live `.venv`; `stockroom shim ensure-env` restored it (torch 2.13.0, DuckDB 2.0.0)
- Measured on DuckDB 2.0.0 (`scratchpad/m3/`): the storage setting's accepted values and new-file tags; zstd on new `v2.0.0` files; in-memory databases accept the clause; old files keep `v1.0.0+` under the setting, and 1.5.4 still reads and writes them; same-path configuration conflicts in one process; the clause fails below `v1.2.0`; v2.1.2's schema-0 leftover is a bare 12,288-byte file; zstd read cost on this machine's tables (from the milestone 2 backup, read-only, SHA unchanged)
- Plan in `tasks.md`: two design questions resolved in plan (an explicit `STORAGE_VERSION = "v2.0.0"` on every engine connect; the runner drops the zstd clause on files older than `v1.2.0`), 6 behaviours (R1, R2, W1 to W4), and steps 0 to 6

## Open for the operator (before build)
- Step 0: where milestone 3's commits go so they stay out of the milestone 1+2 release (pull requests are squash-merged)

## Next Step
- Preflight in a subagent
