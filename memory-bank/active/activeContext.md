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

## Open: editing released migrations (operator, 2026-10-22)
- The operator rejects editing a released migration: it defeats numbered, ordered migrations, because a database that already applied a version never sees the edit. That rules out this plan's zstd edit to `0001`. It also covers milestone 1's change on this branch, which replaced the released `0003` (the HNSW `CREATE INDEX`, which needs `vss`) with comment-only `0003_retired.sql` and changed `0003_snapshot.json`. Comment-only edits to `0001` (milestone 1's, and `main`'s `@rel` lines) change no SQL that runs
- The milestone 1+2 pull request opens only after this is settled
- Facts: v0.1.0 shipped `0001` to `0004`, and every release called `ensure_vss` before migrating. So wild warehouses sit at schema 0 (the bare leftover) or at 4 and above; 1 to 3 only from a crash partway through a first open
- Advisory 3 stays withdrawn; the operator only wanted the reasoning ("you've answered now so good")

## Operator rulings on migrations (2026-10-22)
- Restore every released migration exactly as it shipped. Released migrations may not be rewritten
- A major version break is the only time schema provenance may change in a way that cannot migrate. Even then, a copy-into-a-new-database tool is not an option for stockroom, because plugin distribution through agent harnesses gives no good way to step a user through it
- No runner rule that records version 3 without running it (rejected as conditional logic that breaks the truth of migrations). The baseline idea was not taken up either
- The operator asked whether the cost of the released `0003` is only needing `vss` briefly, and why a new migration cannot add zstd

## Measured for those questions (DuckDB 2.0.0, `scratchpad/m3/probe_answers.py`, `measure_force_zstd.py`)
- Released `0003` without `vss`: CatalogException on its `SET` (no autoload). `INSTALL vss` 0.85 s (download), `LOAD` 0.04 s, 48 MiB extension cache
- A kill after `0003` commits leaves a wal. A reopen without `vss` opens, the index is present, and `0009`'s drop runs
- No `ALTER` sets compression. A rebuild of the column (add, update, drop, rename) gets `BinderException` on a `v1.0.0` file and works on `v2.0.0`. Every existing warehouse is `v1.0.0+`
- `force_compression = 'zstd'` as a connection setting: on `v2.0.0`, every string and JSON column gets ZSTD, integers keep BitPacking, floats keep ALPRD. On `v1.0.0` there is no error, but string segments are written Uncompressed. Real tables: `v2.0.0` 289 MiB forced against 290 MiB with the two-column DDL and 489 MiB with DuckDB's choice; `v1.0.0` 599 MiB forced against 556 MiB with DuckDB's choice

## Operator decisions (2026-10-22, later)
- One migration chain (no second v2 chain). New warehouses are built from a frozen schema file at version 9 (zstd on the two columns, no index), recorded as one `schema_version` row naming that file; they never run `0003`, so nothing loads `vss`. Old warehouses keep the chain (`0009` drops the index) and get zstd from the copy. The empty old-format leftover is renamed aside and a fresh warehouse built (agent proposal, not yet confirmed in detail)
- Format policy (operator): old-format warehouses are not permitted to persist. A warehouse runs to the end of the chain, then converts to the next format; a later format repeats that. For the L4 re-plan: the check's skips (low disk, hard links refused) currently let a file stay old, and future migrations must still run on old-format files, because they migrate before they convert
- The operator asked why not a declarative tool (write only a schema, diff at runtime, as WordPress's `dbDelta` does). Answered in chat: `0002` (add plus drop, which a diff cannot tell from a rename) and `0005` (a data-only reset) cannot be expressed as a schema diff; WordPress itself pairs `dbDelta` with numbered `upgrade_NNN()` routines; no declarative tool was found with DuckDB support, so it would be a home-grown differ; and DuckDB still cannot change compression in place

## Operator rulings (2026-10-22, final in this discussion)
- Keep migrations (the declarative question was only a challenge). One chain forever, plus a frozen schema file pinned to one version. New warehouses are created from it and migrate forward to the tip. Confirmed by the operator
- A warehouse that tries to reach the tip and cannot stops in an error state that users discover and must resolve. Code after the DuckDB 2.0 point never detects an older, unmigrated warehouse (for example, one still at schema 8) and copes with it. No degraded modes
- The copy-and-swap stays: a necessary evil at its point in the chain (the v1-to-v2 format boundary), built as durable, good-practice code, not a short-lived utility, even with about five users today. This replaces the brief's lifetime rule for milestones 5 to 7
- "I think we have a solid plan!": go-ahead for the L4 re-plan. Milestone 3 joins the first release on this branch (the agent's recommendation; not objected to), because restoring the released `0003` breaks new installs until the schema-file path exists

## Next Step
- L4 re-plan: update `projectbrief.md` and `milestones.md` (restore released migrations; schema file for new warehouses; milestones 1 to 3 in the first release; copy-and-swap durable at the format boundary; migrate-or-error), then L4 preflight
