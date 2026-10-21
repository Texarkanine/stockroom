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

## 2026-10-21 - PREFLIGHT - FAIL (fixable)

* Work completed
    - Preflight of the DuckDB 2.0 plan. The plan was not edited. Status is in `memory-bank/active/.preflight-status`
* Decisions made
    - Fixable: the repair has to restore the leftover-`.wal` state and the folded state. One copy that folds before `DROP INDEX` proves only the folded state. The fix is two fresh copies of the baseline
    - Not decided yet: the three advisories. The re-plan records which are adopted
* Insights
    - `uv run --with duckdb==2.0.0` left this checkout's interpreter on 1.5.4. The project virtualenv has no torch. The hashed freeze is at `~/.local/share/stockroom/torch-requirements.txt`

## 2026-10-21 - PLAN (RE-PLAN) - COMPLETE

* Work completed
    - Split the shadow repair into two copies of the baseline. Branch A repairs while the `.wal` exists. Branch B folds, then repairs. Both repeat on a newer 2.0 patch
    - Added the same two branches to `--synthetic`, on small files, before the live copy
* Decisions made
    - Adopted the ingest advisory: an ingest exit of 0 is not an index health check
    - Adopted the torch advisory: the overlay prints DuckDB 2.0.0 and imports torch, installed from the hashed freeze into that overlay only
    - Not adopted as a replacement: moving the kill off the real warehouse. The synthetic branches are a prelude. The Done line still runs both branches on copies of the real baseline
    - An observation probe that hangs is recorded. A repair probe that does not finish fails the script
* Insights
    - Folding the log before `DROP INDEX` removes the leftover-`.wal` state, so one copy cannot prove both repairs


## 2026-10-21 - PREFLIGHT - COMPLETE (FAIL (fixable))

* Work completed
    - Preflight of the DuckDB 2.0 plan. First line of `memory-bank/active/.preflight-status` is `FAIL (fixable)`
* Decisions made
    - The plan changes before build. The shadow repair has to run on a leftover-`.wal` copy and on a folded copy. Folding first leaves the loud state unproven
* Insights
    - On 1.5.4, one row is enough for `EXPLAIN` of the unscoped cosine statement to contain `HNSW_INDEX_SCAN`. `uv run --with duckdb==2.0.0` layered 2.0.0 over `.venv` and left the project interpreter on 1.5.4. This `.venv` has no torch; the hashed freeze is present
