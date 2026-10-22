# Active Context

## Current Task: warehouse-file-growth, milestone 1 (drop the HNSW index and vss)
**Phase:** QA - COMPLETE (PASS)

## What Was Done
- Planning and preflight: see `progress.md`. Operator decisions on the thirteenth preflight: no orphan guard; build in place; advisories 1, 2, 4 to 7 folded; advisory 8 is for milestone 3
- Build, in plan order:
    - Step 1 (`9732611`): `semantic._ranked_hits` is the one exact statement for every scope; `_hnsw_hits`, `_scoped_hits`, and `OVERFETCH` are gone
    - Step 2 (`e1b3d00`): shadow script stripped to guards, copy, checkpoint equality, overlay, live phase, and non-index measurements
    - Step 3 (`5af3bf1`): `0003_retired.sql` (comments only); schema tests and `migrated_con` load no `vss`; five snapshots regenerated with `"indexes": []`
    - Step 4 (`7f1d338`): `0009_drop_vector_index.sql`; `ensure_vss` and its five calls removed; worker builds v2.1.2's indexed schema-8 warehouse in a child; B9 to B15 green. Live-copy proof passed on a 43 GB copy; the live warehouse was migrated and verified (version 9, no index, used blocks 163,283 to 6,862, every row count unchanged)
    - Step 5 (`9a11273`): docs, system model, schema footer, `systemPatterns`, `techContext`
    - Step 6: `make ci` and `make docs-build` pass
- Files created: `migrations/0009_drop_vector_index.sql`, `migrations/0003_retired.sql` (renamed), `tests/test_schema_0009.py`. Modified: `semantic.py`, `warehouse.py`, `embed.py` (docstrings), `0001` (comments), `conftest.py`, `_warehouse_worker.py`, `test_semantic.py`, `test_schema_0003`-`0008`, `test_migrate_runner.py`, `test_warehouse_open.py`, `test_warehouse_concurrency.py`, `test_shadow_duckdb_20.py`, `scripts/shadow_duckdb_20.py`, five snapshots, and the step 5 prose files

## Deviations from the plan
- The landing used one scratch script, `land.py`, instead of hand edits. It applied the planned order (`0009`, then the calls, then the function, then the `embed.py` docstrings) with atomic file replaces, first to the proof copy of `src` and then to the checkout. `diff -ru` showed the checkout's `src` byte-identical to the code the proof ran. The step-4 tests also passed against the proof copy before the landing
- The shadow strip also removed `LOCK_ERROR` and the child prelude's `one_line`, which only deleted code used
- The head-snapshot docstring in `test_warehouse_open` was reworded in step 3, when the snapshot changed, not in step 4
- `test_warehouse_open` imports `_FixedEncoder` from `test_semantic` and `one_hot` from the worker (the suite already imports helpers across test modules)
- The embeddings page and `techContext` say "vector index" and do not name HNSW or `vss` (operator: strip everything about the index except the migration that drops it)

## Integration and proof results
- Live-copy proof (scratch `m1/live_copy_proof.py`): every check passed. The first run stopped at the equality check on a script bug (DuckDB's progress bar on the child's stdout) and was resumed from that check on the migrated copy
- Harness-scope owner sets differed between the old and new SQL in `measure_shapes`. `tie_check.py` over 8 query vectors: every difference sits exactly at the cut distance, and the nearer-than-cut sets are equal. The live data has many identical vectors (one sample had 150 owners at distance 0), so the tie-break decides those
- Timings on the migrated copy (DuckDB 1.5.4, top-100): unscoped 205 ms (old SQL 1,676 ms), `--role user` 445 ms (1,181 ms), `--harness claude` 61 ms (697 ms)
- Machine state: `stockroom shim ensure-env` restored torch for the proof; the pre-commit exact sync removed it again, as before the build. Proof copies deleted; scripts and logs remain under this session's scratchpad `m1/`

## Next Step
- QA runs in a subagent (`/niko-qa`)
