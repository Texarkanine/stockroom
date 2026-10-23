# Active Context

## Current Task: warehouse-file-growth, milestone 3 (restore released migrations, new warehouses from a frozen schema file)
**Phase:** REFLECT - COMPLETE (steps 8.2 and 8.4 passed on Puck, 2026-10-23)

## What Was Done
- Plan (Level 3, 9 steps, 36 behaviours) passed preflight with advisory; the operator ruled on advisories 4 and 5 and the radical innovation (2026-10-23)
- Build steps 0 to 7, 8.1, 8.2, and 8.3 done. Step 8.2 passed on Puck at `ac20922` (ingest 22s, embed 490s, semantic rank 1; scratch file `v2.0.0+`, schema 9, no index, ZSTD, `vss` unloaded). Figures are in `progress.md`. Step 8.4 passed on Puck at `09ea4ae` in 43s (copy stayed `v1.0.0+`; DuckDB 1.5.4 wrote it and 2.0.0 read it)
- Files created: `scripts/check_released_migrations.py`, `skills/sr-search/src/stockroom/storage.py`, `skills/sr-search/src/stockroom/schemas/schema_0009.sql`, `skills/sr-search/tests/test_released_migrations.py`, `skills/sr-search/tests/test_storage.py`, `skills/sr-search/tests/fixtures/schema/0009_snapshot.json`
- Files restored to their `v2.1.3` SQL or bytes: `migrations/0003_embeddings_hnsw_index.sql` (plus one comment paragraph), the `0003`, `0004`, `0006`, `0007`, `0008` goldens. Deleted: `migrations/0003_retired.sql`
- Files changed: `Makefile`, `.github/workflows/ci.yaml`, `warehouse.py`, `migrate.py`, `scripts/shadow_duckdb_20.py`, tests (`conftest.py`, `_warehouse_worker.py`, `test_schema_0003.py` to `test_schema_0009.py`, `test_migrate_runner.py`, `test_warehouse_open.py`, `test_warehouse_concurrency.py`, `test_migrate_cli.py`, `test_shadow_duckdb_20.py`), docs (`docs/architecture/warehouse.md`, `docs/contributing/iteration/engine.md`), `memory-bank/systemPatterns.md`, `memory-bank/techContext.md`
- Verification: `make ci` exit 0 (1,085 passed, 39 skipped; 134 JS; gate and schema docs green; REUSE compliant). Torch-gated modules after `ensure-env`: 111 passed, 2 skipped (the intended inverse skip). Live checks: `stockroom migrate` reports schema 9; the live file's SHA-256 is unchanged by the open (`20894505…6a2d`, same as the morning backup); tag `v1.0.0+`; no index
- PR 150 opened from `feat/duckdb-2-new-warehouses` (this branch minus `memory-bank/active/`). User-facing docs on that branch describe the current cutoffs and the schema snapshot. The below-schema-3 stop has no troubleshooting heading yet

## Operator decisions
- 2026-10-23 (preflight review): advisory 5, a new warehouse goes into place with `os.rename` after a check under the writer flock, not a hard link (advisory 4 no longer applies). Radical innovation reduced: W6's schema 3 to 8 files are written by DuckDB 1.5.4 with its `vss`
- 2026-10-23 (build): a scratch ingest on the WSL machine takes hours, so the real-data run (step 8.2) runs on Puck (M5 Mac, smaller warehouse) by Tachi, from a fresh clone of the pushed branch. The new-warehouse path has no platform-specific code (`os.rename`, file and folder `fsync`, `fcntl.flock`; same DuckDB 2.0 and zstd), so a Mac run stands in for this machine's

## Build decisions and deviations
- Branch: the build stays on `constrain-size-as-best-we-can`; `milestones.md` (amended 2026-10-22) ships milestones 1 to 3 in one pull request
- S1 builds its chain file at `STORAGE_VERSION`: a `v1.0.0` file reloads the view's SQL with one fewer `)` (DuckDB 2.0.0), which is storage, not schema
- `create_warehouse` also removes the temp file when the build raises (S10 and W9 check it); a killed build still leaves one for the next creation
- `released_chain_file` takes an optional `dest`; W7's schema-8 tests use it (a cached child-built copy) instead of spawning `build_chain` per test
- Shared constants for the 1.5.4 fixture (`RELEASED_DUCKDB`, `INDEXED_VERSIONS`, `RELEASED_CHAIN_154_ROWS`) live in `_warehouse_worker.py`, like `KILLED_SLOT`
- R6 also pins the released filename `0003_embeddings_hnsw_index.sql`, so it fails while the retired file is in place
- The restored `0003` to `0008` tests keep their released shape; only the chain source changed (child-built copies instead of an in-process `ensure_vss`)
- The shadow script's docstring says the synthetic section downloads `vss` once
- Found during the run: a bare full `pytest` in this live checkout drops torch midway (`test_coverage_collection` runs `make coverage-engine`, whose `sync` is exact). Predates this milestone; SumMem note
- Found during the stopped real-data run: a read-only open of a zstd file with a `.wal` shows the replayed rows as `persistent = false`, `Uncompressed`; every persistent segment was `ZSTD`. Milestones 4 and 6 must count persistent segments only, or check with no `.wal` (SumMem note)

## Step 8.2 on Puck

Done 2026-10-23 at `ac20922`, from a fresh clone and a scratch home. Ingest exit 0 in 22s, embed exit 0 in 490s (10,715 vectors, no `nanobind:` line), semantic exit 0 in 5s with a rank-1 row. The scratch file stayed `v2.0.0+`, schema `(9, 'schema_0009.sql')`, no index, both large columns `ZSTD`, `vss` unloaded. Size 12,070,912 bytes after ingest and 25,440,256 after embed. The live warehouse was unchanged. Full figures are in `progress.md`. The scratch home and the clone are removed.

Step 8.4 passed on Puck 2026-10-23 at `09ea4ae`, from a fresh clone, in 43s. `shadow: every phase passed`. The copy stayed `v1.0.0+`, at the schema head, with no index. Six tables matched the baseline in both directions. Ingest added 1 cursor session. Embed wrote 17 chunk vectors for 14 messages, and the log has no `nanobind:` line. Semantic returned a rank-1 row. DuckDB 1.5.4 wrote the copy and DuckDB 2.0.0 then answered the same cosine query (100 rows). The live warehouse was unchanged: 404,238,336 bytes, inode 2166990, mtime 2026-10-23 06:26:45. The scratch home and the clone are removed.

## Reflection
- `memory-bank/active/reflection/reflection-warehouse-file-growth-m3.md`. Main points: the plan held in order and scope; the one build surprise (view SQL differs by storage version) came from a technology probe run in one configuration and a test planned in another; the real-data run needed a timed sample at plan time. After QA, three change-detector lines and `0009`'s stale wording were fixed. `techContext.md` gained one pointer: the pytest process never loads `vss`, and released-chain test files come from the child-built fixtures

## Next Step
- Do not run `/niko` step 2a and do not start milestone 4 until the operator says so. Milestone 3 stays unchecked in `milestones.md`
- Next window: add a user-guide troubleshooting heading for the below-schema-3 stop (the file is untouched and holds no history; `stockroom migrate` prints one line with the `mv` and exits 1; `stockroom ingest` raises the same error without that one-line form). Link it from the stop paragraph in `docs/architecture/warehouse.md`. There is no such heading today
- PR 150 is open and not draft: https://github.com/Texarkanine/stockroom/pull/150 — title `feat!: drop the HNSW index and create new warehouses in DuckDB 2.0 format`, base `main`, does not close issue 147. Branch `feat/duckdb-2-new-warehouses` (tip `d11f0ab` when this was written). This repo squash-merges, so after it lands do not rebase `constrain-size-as-best-we-can` onto `main` and do not merge the release branch back. Branch from `main` and restore `memory-bank/active/` from this branch in one commit
- Uncommitted on this branch, left for the next window: `docs/architecture/warehouse.md` deletes the heading `#### When open() does not run every migration`. Do not commit `.cursor/skills/stockroom-local/`
