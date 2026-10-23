# Active Context

## Current Task: warehouse-file-growth, milestone 3 (restore released migrations, new warehouses from a frozen schema file)
**Phase:** BUILD - COMPLETE (real-data run of the new-warehouse path handed to Tachi on Puck; see the handoff below)

## What Was Done
- Plan (Level 3, 9 steps, 36 behaviours) passed preflight with advisory; the operator ruled on advisories 4 and 5 and the radical innovation (2026-10-23)
- Build steps 0 to 7 and 8.1 and 8.3 done; 8.2 is with Tachi on Puck (operator, 2026-10-23); 8.4 (personal Mac shadow re-run) is the operator's release gate
- Files created: `scripts/check_released_migrations.py`, `skills/sr-search/src/stockroom/storage.py`, `skills/sr-search/src/stockroom/schemas/schema_0009.sql`, `skills/sr-search/tests/test_released_migrations.py`, `skills/sr-search/tests/test_storage.py`, `skills/sr-search/tests/fixtures/schema/0009_snapshot.json`
- Files restored to their `v2.1.3` SQL or bytes: `migrations/0003_embeddings_hnsw_index.sql` (plus one comment paragraph), the `0003`, `0004`, `0006`, `0007`, `0008` goldens. Deleted: `migrations/0003_retired.sql`
- Files changed: `Makefile`, `.github/workflows/ci.yaml`, `warehouse.py`, `migrate.py`, `scripts/shadow_duckdb_20.py`, tests (`conftest.py`, `_warehouse_worker.py`, `test_schema_0003.py` to `test_schema_0009.py`, `test_migrate_runner.py`, `test_warehouse_open.py`, `test_warehouse_concurrency.py`, `test_migrate_cli.py`, `test_shadow_duckdb_20.py`), docs (`docs/architecture/warehouse.md`, `docs/contributing/iteration/engine.md`), `memory-bank/systemPatterns.md`, `memory-bank/techContext.md`
- Verification: `make ci` exit 0 (1,085 passed, 39 skipped; 134 JS; gate and schema docs green; REUSE compliant). Torch-gated modules after `ensure-env`: 111 passed, 2 skipped (the intended inverse skip). Live checks: `stockroom migrate` reports schema 9; the live file's SHA-256 is unchanged by the open (`20894505…6a2d`, same as the morning backup); tag `v1.0.0+`; no index

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

## Handoff: real-data run on Puck (for Tachi)

Purpose: prove the new-warehouse path on real transcripts (brief acceptance 12, plan step 8.2). A new scratch home gets a warehouse built from `schema_0009.sql`. Then ingest, embed, and semantic search must work. Do not use or change the real stockroom home, the real warehouse, or the `stockroom` command on the machine.

1. Make a fresh clone of the branch. Do not use an existing checkout.

   ```sh
   git clone --branch constrain-size-as-best-we-can https://github.com/Texarkanine/stockroom.git stockroom-m3
   cd stockroom-m3
   git rev-parse --short HEAD
   make sync
   ```

   Record the commit. Do not run `make shim` or `make torch` in this clone.

2. Set these shell variables. `SCRATCH` must be a new, empty folder outside the real stockroom home.

   ```sh
   ENGINE="$PWD/skills/sr-search"
   SCRATCH="$(mktemp -d)/home"
   sr() { STOCKROOM_HOME="$SCRATCH" PYTHONPATH="$ENGINE/src" uv run --project "$ENGINE" --no-config --no-sync python -m stockroom "$@"; }
   ```

3. Run the ingest. Record the time and the exit code.

   ```sh
   time sr ingest --verbose
   ```

4. Check the new file. Every line must match the comment above it.

   ```sh
   uv run --project "$ENGINE" --no-config --no-sync python - "$SCRATCH/warehouse.duckdb" <<'EOF'
   import sys, os, duckdb
   db = sys.argv[1]
   con = duckdb.connect(db, read_only=True)
   q = lambda sql: con.execute(sql).fetchall()
   # size in bytes, and no .wal: False
   print("size", os.path.getsize(db), "wal", os.path.exists(db + ".wal"))
   # tag: v2.0.0+
   print("tag", q("select tags from duckdb_databases() where database_name = current_database()")[0][0]["storage_version"])
   # schema_version: [(9, 'schema_0009.sql')]
   print("schema_version", q("select version, filename from schema_version order by version"))
   # indexes: []
   print("indexes", q("select index_name from duckdb_indexes() where not is_primary"))
   # codecs: only ZSTD for both columns
   for t, c in (("messages", "text"), ("tool_calls", "tool_input")):
       print("codecs", t, c, q(f"select distinct compression from pragma_storage_info('{t}') where column_name = '{c}' and segment_type != 'VALIDITY' and persistent"))
   # rows: sessions, messages, tool_calls all more than 0
   print("rows", [q(f"select count(*) from {t}")[0][0] for t in ("sessions", "messages", "tool_calls", "embeddings")])
   # vss: False
   print("vss", q("select loaded from duckdb_extensions() where extension_name = 'vss'")[0][0])
   con.close()
   EOF
   ```

5. Put torch into the clone. Do not set `STOCKROOM_HOME` for this step: the command reads the hashed torch freeze from the real stockroom home. It changes only the clone's `.venv`. It does not change the `stockroom` command.

   ```sh
   PYTHONPATH="$ENGINE/src" uv run --project "$ENGINE" --no-config --no-sync python -m stockroom shim ensure-env --app-dir "$ENGINE"
   uv run --project "$ENGINE" --no-config --no-sync python -c "import torch; print(torch.__version__)"
   ```

   The second command must print a version. If it fails, stop and tell the operator.

6. Run the embed. Record the time and the exit code. The output must not contain a line that starts with `nanobind:`. If the embed runs for more than 60 minutes, stop it with Ctrl-C and tell the operator.

   ```sh
   time sr embed --verbose
   ```

7. Run one search. The output must contain a row that starts with rank `1`.

   ```sh
   sr semantic "how does the warehouse lock work"
   ```

8. Do step 4 again. Record the new size and the embeddings count.

9. Send the operator: the commit from step 1, the times and exit codes from steps 3 and 6, all output from steps 4 and 8, and the first lines from step 7.

10. Remove the scratch folder and the clone.

    ```sh
    rm -rf "$(dirname "$SCRATCH")"
    cd .. && rm -rf stockroom-m3
    ```

Also pending on Puck, only when the operator asks: the release gate (plan step 8.4). That is the shadow test from a fresh clone of the same branch, as in the docstring of `scripts/shadow_duckdb_20.py`. Its synthetic section now downloads `vss` once.

## Next Step
- QA (`/niko-qa` in a subagent), then reflect. The Puck real-data result goes into `progress.md` when the operator relays it; it is needed before the milestone 1 to 3 pull request opens
