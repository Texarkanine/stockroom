# Active Context

## Current Task: warehouse-file-growth, milestone 3 (restore released migrations, new warehouses from a frozen schema file)
**Phase:** PREFLIGHT - COMPLETE (PASS WITH ADVISORY)

## What Was Done
- Milestone 3 classified Level 3; the L4 preflight status file cleared
- Wrote the Level 3 plan in `tasks.md`: 9 steps (0 backup, 1 immutability gate, 2 schema file and `stockroom.storage`, 3 create through `open()` and the floor stop, 4 `migrated_con` from the schema file, 5 restore the released migrations and goldens, 6 shadow script's synthetic builder, 7 docs and memory bank, 8 verification gates) and 35 behaviours (G1 to G8, S1 to S10, W1 to W8, R1 to R7, H1 to H2)
- Measured on DuckDB 2.0.0 (scratchpad `m3/`): tests can build the released chain in a child that loads `vss` and read the file without it. Without `vss`, an explicit `CHECKPOINT` after a change, before `0009`, is fatal, but a plain close and the runner's real path are fine. A schema file in the chain's column order matches the chain at 9 apart from the zstd clause. Building at a temp path with `v2.0.0`, then a plain connect after the rename, works. The gate's token comparison accepts the real comment-only edits
- Recorded the unbound-index checkpoint fact in SumMem

## Decisions (agent, in the plan)
- The pytest process never loads `vss`: the released chain is built in a child; the `0003` live-index check runs whole in the child
- The floor check (below schema 3) lives in `warehouse.py`; new `WarehouseUnmigratableError`; `stockroom migrate` prints it as one line
- A new warehouse goes into place with `os.link` then `os.unlink` of the temp name: a rename that can never replace an existing file
- Names: `stockroom.storage`, `src/stockroom/schemas/schema_0009.sql`, temp `warehouse.building.duckdb`
- Gate: `scripts/check_released_migrations.py` compares SQL tokens against the highest `v*` tag, for `migrations/` and `schemas/`; `make migrations-check` in `make ci`; CI checkout `fetch-depth: 0`
- Real-data run: full ingest and embed in a scratch home with a 60-minute bound (CUDA available)

## Next Step
- Preflight (subagent) on the Level 3 plan
