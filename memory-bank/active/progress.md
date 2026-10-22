# Progress

L4 milestone 1 of 7 for `warehouse-file-growth` ([issue 147](https://github.com/Texarkanine/stockroom/issues/147), as amended in `memory-bank/active/projectbrief.md`): drop the HNSW index with a migration, and remove the `vss` extension and everything else about the index from the engine. Semantic search becomes one exact path that keeps the nearest chunk per message owner and cuts to the limit before it joins `messages`. Before the first commit that contains the migration, the migration runs on a copy of this machine's warehouse. `make ci` passes on DuckDB 1.5.4.

The L4 plan's history (twelve preflights, the failed DuckDB 2.0 sub-run, the re-plan, and the operator review) is in git at `9a3fb7a`, in this file.

**Complexity:** Level 3

## 2026-10-22 - COMPLEXITY ANALYSIS - COMPLETE

* Work completed
    - Classified milestone 1, "Drop the HNSW index with a migration and remove the vss extension and everything else about the index from the engine"
* Decisions made
    - Level 3, as the L4 plan estimated. A new migration, the warehouse chokepoint, semantic search, schema snapshots and the ERD, tests, docs, the system-model reference, memory-bank context, and the shadow script all change. The first commit that contains the migration drops the index on this machine's live warehouse

## 2026-10-22 - PLAN - COMPLETE

* Work completed
    - Wrote the Level 3 plan in `tasks.md`: 6 steps (exact search, retire `0003`, strip the shadow script, `0009` with the `ensure_vss` removal and a live-copy proof, docs and context, full verification) and 16 behaviours
    - Measured exact-search statements on read-only copies of this machine's data (`scratchpad/m1/measure_shapes.py`), and probed DuckDB 1.5.4 writes against an unbound HNSW index (`scratchpad/m1/unbound_index_probe.py`)
* Decisions made
    - One exact statement for every scope: nearest chunk per owner, ordered by distance then harness then owner id, cut to the limit, then a join to `messages` for text. A `--role` scope joins `messages` keys and role inside the ranking. Top-100 over 133,793 vectors: 220 ms on 1.5.4, about 160 ms on 2.0.0; today's scoped SQL takes 1.7 s and about 2 s
    - No orphan guard in the ranking. The shipped writer cannot make an orphan, embed sweeps them nightly, the live data has 0, and a guard costs 2.5 times as much on 1.5.4. A test pins that an orphan is left out without an error
    - `0003` becomes `0003_retired.sql`, comment-only; `0009_drop_vector_index.sql` runs `DROP INDEX IF EXISTS embeddings_vector_hnsw`. Snapshots `0003` to `0008` are regenerated with no index; `0009` reuses the `0008` snapshot
    - Landing order: steps 1 to 3 first (safe with the live index present); then the tests for step 4 run red; then the proof on a fresh copy of the live warehouse with a scratch copy of `src`; then `0009` and the `ensure_vss` removal in one response; then `stockroom migrate` on the live warehouse, verified read-only, before the first commit that contains `0009`
* Insights
    - The live shim runs this checkout's working tree, not its commits, so a saved file is live at once. The milestone's "first commit is live" understated this
    - On DuckDB 1.5.4 without `vss`, every `INSERT` or `DELETE` on `embeddings` fails while the HNSW index exists, even a delete that matches nothing; `DROP INDEX IF EXISTS` inside a transaction works. So removing `ensure_vss` before `0009` would break the nightly ingest and embed, and an empty stub `0009` would record version 9 without dropping the index

## 2026-10-22 - PREFLIGHT - COMPLETE

* Work completed
    - Level 3 preflight of the milestone 1 plan; `.preflight-status` first line: `PASS WITH ADVISORY`
    - All seven Level 2/3 checks pass. `tasks.md` was not changed (no TDD swap, no strike)
    - Measured on DuckDB 1.5.4 and 2.0.0 (`pf13/killed_migrator_probe.py` in this session's scratchpad): a migrator with no `vss`, killed after it committed the `0009` drop, leaves a `.wal` that a no-`vss` open replays (no index, every row, version 9). A `vss` writer killed after an insert leaves a `.wal` that a no-`vss` open replays, then the drop, an insert, and the exact search work. A comment-only migration runs through `con.execute` outside and inside a transaction. `duckdb_extensions()` lists `vss` even when it is not installed
* Decisions made
    - Eight advisories, none adopted yet: in step 4.5, write `0009` before removing `ensure_vss`, and remove the calls before the definition; B12 passes in step 4's red run (move it to step 2); the orphan rationale misses an interrupted autocommit `write_session` (key-join guard costs about 57 ms on 2.0.0); add `test_schema_0007._apply_through` to step 2.3; take verify_live's "before" record before landing; pin the scratch scripts' absolute paths; do step 3 before step 2; milestone 3's zstd `0001` will break `build_v2_1_2_chain`
    - Radical advisory, not applied: build in a git worktree so nothing is live until one fast-forward, and the live-copy proof runs the exact code that lands

## 2026-10-22 - REVIEW (OPERATOR) - COMPLETE

* Work completed
    - Folded the thirteenth preflight's six correction advisories into `tasks.md`, and corrected the orphan reasoning
* Decisions made
    - Operator: no orphan guard in exact search (advisory 3). The plan's premise was wrong: `write_session` commits each statement separately, so an ingest crash can leave orphans until the next ingest or embed, and a top-k search can be short then. The guard's cost (+57 ms on 2.0.0, +340 ms on 1.5.4) was not taken
    - Operator: build in place, not in a git worktree (radical advisory)
    - Operator: accept advisories 1, 2, 4, 5, 6, and 7. Landing order is `0009` first, then the `ensure_vss` calls, then the function; B12 moves to the retire-`0003` step; `test_schema_0007._apply_through` joins the cleanup; the live before record comes just before landing; scratch scripts have full paths; the shadow strip (now step 2) runs before retiring `0003` (now step 3)
    - Advisory 8 is for milestone 3: the old-chain builder will need v2.1.2's `0001` once `0001` gains zstd
* Insights
    - Writing `0009` first removes every unsafe moment from the landing, so the build needs no "never stop between two edits" rule

## 2026-10-22 - BUILD - COMPLETE

* Work completed
    - All six plan steps, committed per step (`9732611`, `e1b3d00`, `5af3bf1`, `7f1d338`, `9a11273`). Red runs before every executable change: step 1 (B1 one owner of three, B2 `KeyError`; B3 and B5 already passed), step 3 (24 failures on `0003`'s `vss`-only `SET`, and B12), step 4 (16 failures: no `0009`, `vss` loaded, head 8)
    - Live-copy proof on a 43 GB copy of this machine's warehouse, then the landing, then `stockroom migrate` on the live warehouse, verified against a read-only before record
    - `make ci` and `make docs-build` pass: pytest 1,040 passed, 38 skipped
* Decisions made
    - The landing went through one scratch script applied identically to the proof copy and the checkout, so the proof ran the exact code that landed (a byte diff confirmed it)
    - Docs name the removed thing "vector index", not HNSW or `vss`, per the operator's strip instruction
* Insights
    - The live data has many identical vectors, so equal distances at the cut are common; the old scoped SQL broke them arbitrarily, and the new tie-break (harness, then message id) is what makes results repeatable
    - DuckDB's Python client draws a progress bar on stdout for long queries; a child whose stdout is parsed needs `SET enable_progress_bar = false`
    - The live drop and close took 0.9 s; the same drop on the cold copy took 19.6 s at close

