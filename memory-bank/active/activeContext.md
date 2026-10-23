# Active Context

## Current Task: warehouse-file-growth, milestone 3 (restore released migrations, new warehouses from a frozen schema file)
**Phase:** PREFLIGHT - COMPLETE (PASS WITH ADVISORY); operator review folded in

## What Was Done
- Milestone 3 classified Level 3; the L4 preflight status file cleared
- Level 3 plan in `tasks.md`: 9 steps (0 backup, 1 immutability gate, 2 schema file and `stockroom.storage`, 3 create through `open()` and the floor stop, 4 `migrated_con` from the schema file, 5 restore the released migrations and goldens, 6 shadow script's synthetic builder, 7 docs and memory bank, 8 verification gates) and 36 behaviours (G1 to G8, S1 to S10, W1 to W9, R1 to R7, H1 to H2)
- Measured on DuckDB 2.0.0 (scratchpad `m3/`): tests can build the released chain in a child that loads `vss` and read the file without it. Without `vss`, an explicit `CHECKPOINT` after a change, before `0009`, is fatal, but a plain close and the runner's real path are fine. A schema file in the chain's column order matches the chain at 9 apart from the zstd clause. Building at a temp path with `v2.0.0`, then a plain connect after the rename, works. The gate's token comparison accepts the real comment-only edits
- Preflight (second run, on Opus; the first, on Fable 5.1, stopped on a usage-credit 429 before writing anything): `PASS WITH ADVISORY`, ten advisories, none blocking

## Operator decisions (2026-10-23, preflight review)
- Advisory 5: a new warehouse goes into place with `os.rename` after a check, under the writer flock, that no warehouse file exists. Not a hard link, so new installs do not depend on hard links. Advisory 4 (a second name after a crash) no longer applies
- Radical innovation, reduced: W6's schema 3 to 8 files are written by DuckDB 1.5.4 with its `vss` (one `uv run --with duckdb==1.5.4` child per pytest worker, from the packaged chain). The other old-format test files stay 2.0.0-written. The full per-tag release matrix was not chosen

## Agent decisions (plan and advisories)
- The pytest process never loads `vss`: the released chain is built in a child; the `0003` live-index check runs whole in the child
- The floor check (below schema 3) lives in `warehouse.py`; new `WarehouseUnmigratableError`; `stockroom migrate` prints it as one line
- Names: `stockroom.storage`, `src/stockroom/schemas/schema_0009.sql`, temp `warehouse.building.duckdb`
- Gate: `scripts/check_released_migrations.py` compares SQL tokens against the highest `vX.Y.Z` tag, for `migrations/` and `schemas/`; `make migrations-check` in `make ci`; CI checkout `fetch-depth: 0`
- Advisories adopted: 1 (git identity and no signing in the gate's temp repos), 2 (only `vX.Y.Z` tags), 3 (creation inside the flock-releasing `try`, new test W9), 6 (steps 5 and 6 in one commit; drop the unused import), 7 (copy today's `0008` golden to `0009` before restoring), 9 (`ensure-env` and a torch import check before the scratch embed)
- Advisory 8 accepted as is, noted for QA: only `stockroom migrate` prints the stop error as one line; other commands show a traceback whose last line names the file and the remedy
- Real-data run: full ingest and embed in a scratch home with a 60-minute bound (CUDA available)

## Next Step
- Operator: `/niko-build` to run the build (step 0, the live backup, comes first)
