# Progress

Move the engine to DuckDB 2.0 and prove it on a copy of a real warehouse. This is the first milestone of `warehouse-file-growth`. The pin, the dependency range, the shadow-test script, and the user-facing statement of which DuckDB versions can open the warehouse belong to this sub-run. The 2.0 lock is the last change this sub-run brings into this checkout.

**Complexity:** Level 3

## 2026-10-21 - COMPLEXITY ANALYSIS - COMPLETE

* Work completed
    - Classified the first unchecked milestone, "Move the engine to DuckDB 2.0 and prove it on a copy of a real warehouse"
* Decisions made
    - Level 3. The work is one feature across the lock, Dependabot, durable tests, a shadow-test script, and `docs/advanced/duckdb.md`. The architectural choices are already in the milestone list, so this is not a new Level 4. It is not a single-component enhancement: the proof runs against a copy of the live warehouse, and the lock must not land here until that proof passes
* Insights
    - The parent Level 4 record stays in git at `95cf742`. This file is the sub-run's record

## 2026-10-21 - PLAN - COMPLETE

* Work completed
    - Wrote the Level 3 plan for the DuckDB 2.0 milestone in `memory-bank/active/tasks.md`
    - Named the storage tag: `duckdb_databases().tags['storage_version']`, `v1.0.0+` on a file created at `v1.0.0`
* Decisions made
    - No open questions. The shadow script is `scripts/shadow_duckdb_20.py`. Durable tests cover the schema-1 tag, the unscoped HNSW plan, and the script's guards
    - The pin commit is last. The Mac runs of the script stay the operator's step before the release
* Insights
    - `make format` syncs the lock, and the commit hook runs it. Editing the lock and committing are the same event on this machine
