# Progress

L4 milestone 1 of 7 for `warehouse-file-growth` ([issue 147](https://github.com/Texarkanine/stockroom/issues/147), as amended in `memory-bank/active/projectbrief.md`): drop the HNSW index with a migration, and remove the `vss` extension and everything else about the index from the engine. Semantic search becomes one exact path that keeps the nearest chunk per message owner and cuts to the limit before it joins `messages`. Before the first commit that contains the migration, the migration runs on a copy of this machine's warehouse. `make ci` passes on DuckDB 1.5.4.

The L4 plan's history (twelve preflights, the failed DuckDB 2.0 sub-run, the re-plan, and the operator review) is in git at `9a3fb7a`, in this file.

**Complexity:** Level 3

## 2026-10-22 - COMPLEXITY ANALYSIS - COMPLETE

* Work completed
    - Classified milestone 1, "Drop the HNSW index with a migration and remove the vss extension and everything else about the index from the engine"
* Decisions made
    - Level 3, as the L4 plan estimated. A new migration, the warehouse chokepoint, semantic search, schema snapshots and the ERD, tests, docs, the system-model reference, memory-bank context, and the shadow script all change. The first commit that contains the migration drops the index on this machine's live warehouse
