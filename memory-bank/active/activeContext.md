# Active Context

## Current Task: warehouse-file-growth, milestone 3 (new file format)
**Phase:** PREFLIGHT - COMPLETE (PASS WITH ADVISORY)

## What Was Done
- Milestone 2 checked off; its sub-run files cleared. Milestone 3 classified Level 3
- After the classification commit, the commit hook stripped torch from the live `.venv`; `stockroom shim ensure-env` restored it (torch 2.13.0, DuckDB 2.0.0)
- Measured on DuckDB 2.0.0 (`scratchpad/m3/`): the storage setting's accepted values and new-file tags; zstd on new `v2.0.0` files; in-memory databases accept the clause; old files keep `v1.0.0+` under the setting, and 1.5.4 still reads and writes them; same-path configuration conflicts in one process; the clause fails below `v1.2.0`; v2.1.2's schema-0 leftover is a bare 12,288-byte file; zstd read cost on this machine's tables (from the milestone 2 backup, read-only, SHA unchanged)
- Plan in `tasks.md`: two design questions resolved in plan (an explicit `STORAGE_VERSION = "v2.0.0"` on every engine connect; the runner drops the zstd clause on files older than `v1.2.0`), 6 behaviours (R1, R2, W1 to W4), and steps 0 to 6
- Preflight: PASS WITH ADVISORY (eight advisories, `.preflight-status`)
- Personal Mac shadow gate passed on Puck, 2026-10-22, against `ce16489`. Fresh clone of `constrain-size-as-best-we-can`, `make sync`, no `--with`, no `make shim`. `scripts/shadow_duckdb_20.py` copied `~/.local/share/stockroom/warehouse.duckdb` (383,791,104 bytes, no `.wal`) and exited 0 with `shadow: every phase passed`. The copy stayed `v1.0.0+`; six tables equalled the baseline; schema at head; no index. Ingest added 2 Cursor sessions, 28 messages, and 54 tool calls. Embed wrote 66 chunks and removed 0 orphans. Semantic returned a rank-1 row. DuckDB 1.5.4 wrote the copy and answered cosine with 100 rows; 2.0.0 answered after that. No `nanobind` line. The live file's mtime stayed 2026-10-22 03:31:55. Scratch clone and home were removed. The work Mac was not run.

## Operator decisions (2026-10-22, preflight review)
- Advisory 1 adopted: brief requirement 2 corrected. On DuckDB 2.0.0, `duckdb_tables().sql` shows `USING COMPRESSION ZSTD` (re-checked); milestone 5's catalog comparison must allow for it
- Advisory 2 adopted: R1 tests `v1.0.0` only; a `v1.1.0` setting persists as `v1.0.0+`
- Advisory 3 not adopted: the operator asked why, and the agent withdrew it. A fresh ingest cannot match live row counts, because the warehouse keeps rows whose transcripts are gone, and W2 plus the planning measurement already cover format, zstd, size, and copy time
- Advisories 4 and 5 adopted: a runner-rule line in `test_migrate_runner.py`'s module docstring; one shared `data_codecs` helper in `conftest.py`
- Advisory 6 / step 0: the operator accepted the agent's recommendation. Milestone 3 builds on a new branch from this branch's tip; `constrain-size-as-best-we-can` stays the milestone 1+2 branch and is pushed to origin so another machine can pull and try it. The milestone 1+2 pull request is not opened yet
- Advisory 8 declined: no shared `storage_facts()` in this milestone; milestones 4 and 6 add one if they need it
- Release gate: the shadow script runs on the personal Mac only, not the work Mac. It passed on Puck on 2026-10-22 (see What Was Done). The work Mac was not run.
- The operator asked why `0001` is edited rather than a new migration or a new tree; answered in chat (existing files never re-run `0001`; compression can only be set in `CREATE TABLE`; a new migration would have to rebuild populated tables, which the brief forbids)

## Next Step
- `/niko-build`. The personal Mac shadow gate has passed. Build starts with step 0 (new branch from this branch's tip), then step 1 (backup and real-data proof)
