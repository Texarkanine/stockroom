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

## 2026-10-21 - PREFLIGHT (SECOND RUN) - FAIL (fixable)

* Work completed
    - Preflight of the revised plan. The plan was not edited. Status is in `memory-bank/active/.preflight-status`
* Decisions made
    - Fixable: ingest, embed, and semantic under the 2.0 overlay must be `sys.executable` with `PYTHONPATH=skills/sr-search/src`. A nested `uv run` stays on the project interpreter, DuckDB 1.5.4
    - Fixable: `make ci` syncs the new lock into `.venv` before the commit. A failed gate restores the 1.5.4 lock and runs `make sync` before the next nightly job
* Insights
    - `package = false` means the overlay does not import `stockroom` until `PYTHONPATH` includes `skills/sr-search/src`

## 2026-10-21 - PLAN (SECOND RE-PLAN) - COMPLETE

* Work completed
    - Pointed ingest, embed, and semantic at the overlay interpreter with `PYTHONPATH=skills/sr-search/src`, and required those imports before the live copy
    - Stated that `make ci` is the sync that moves `.venv`, and that a failed gate restores the 1.5.4 lock and runs `make sync` before 03:30
* Decisions made
    - Adopted the schema-1 setup from `test_open_current_refuses_stale_schema_without_migrating`, including the `filename` column
    - Adopted a fixed free-space margin of 1 GiB above two copies
    - Adopted the home-guard check on directory entry names
    - Adopted the overlay pytest of the two durable tests before `uv lock`
    - The 1.5.4 writer stays a nested `uv run`, which is what puts it on the project interpreter
* Insights
    - A nested `uv run` from inside the overlay ignores `VIRTUAL_ENV` and uses `skills/sr-search/.venv`

## 2026-10-21 - PREFLIGHT (THIRD RUN) - FAIL (fixable)

* Work completed
    - Preflight of the second re-plan. The plan was not edited. Status is in `memory-bank/active/.preflight-status`
* Decisions made
    - Fixable: repair runs only after the copy is classified. Loud means the wal remains and a probe hung or raised. Folded means the wal is gone and the index count is lower than the row count. A healthy index must not walk into a passing repair
* Insights
    - Killing when the wal file appears can be before the insert commits. The kill is SIGKILL after a commit that stays under `checkpoint_threshold`

## 2026-10-21 - PLAN (THIRD RE-PLAN) - COMPLETE

* Work completed
    - Repair now waits on `classify`. Loud is a remaining wal plus a hung or raised probe. Folded is a gone wal plus an index count below the row count
    - The kill is SIGKILL after the child commits an insert that stays under `checkpoint_threshold`
* Decisions made
    - Adopted the read-only used-block and distinct-block print after the leaking delete
    - Adopted the row check that lets `embeddings` shrink by the orphan count embed reports
    - Adopted one `classify` function shared by synthetic, live, and the patch repeat
    - Not adopted: a JSON phase file under the scratch home. The script prints the facts
* Insights
    - A repair that finishes on a healthy index is not evidence the replay bug was present

## 2026-10-21 - PREFLIGHT (FOURTH RUN) - FAIL (fixable)

* Work completed
    - Preflight of the classification re-plan. The plan was not edited. Status is in `memory-bank/active/.preflight-status`
* Decisions made
    - Fixable: compare the embeddings count, taken before SIGKILL, immediately after the repair checkpoint. The later probes only have to finish
    - Fixable: a failure to open the file is not the loud state. Loud is a remaining wal plus a probe that opened the database and then hung or raised
    - Fixable: the patch repeat accepts only final `2.0.N` versions. `2.0.0.dev*` uploads sort after `2.0.0` and are ignored
* Insights
    - PyPI's newest stable duckdb today is 2.0.0, so the repeat prints that and skips

## 2026-10-21 - PLAN (FOURTH RE-PLAN) - COMPLETE

* Work completed
    - The embeddings count is taken from the child before SIGKILL and compared immediately after the repair checkpoint. The later probes only have to finish
    - `classify` returns `blocked` when a probe does not open or reports a lock error. Loud requires a probe that opened and then hung or raised
    - The patch repeat keeps final `2.0.N` versions only
* Decisions made
    - Adopted `--no-sync` on the shadow `uv run`
    - Adopted binding the vector on `EXPLAIN`
    - Adopted four direct tests of the pure `classify` function
* Insights
    - A second open of a file this process still holds raises `IOException` on DuckDB 1.5.4. That is not the replay bug

## 2026-10-21 - PREFLIGHT (FIFTH RUN) - FAIL (fixable)

* Work completed
    - Preflight of the fourth re-plan. The plan was not edited. Status is in `memory-bank/active/.preflight-status`
* Decisions made
    - Fixable: the patch-repeat child has to start with `VIRTUAL_ENV` unset. From inside the overlay, a nested `uv run --with` ignores the requested DuckDB and runs the project interpreter
* Insights
    - PyPI's newest final duckdb is still 2.0.0, so the skip branch is what runs today. The command has to select a later patch when one exists

## 2026-10-21 - PLAN (FIFTH RE-PLAN) - COMPLETE

* Work completed
    - The 1.5.4 writer and the patch child start with `VIRTUAL_ENV` unset. Each prints `duckdb.__version__`, and the phase fails on a mismatch
    - The synthetic `checkpoint_threshold` is set after the index is checkpointed, above the insert's wal
    - The folded check reads the `count` column of `pragma_hnsw_index_info()`
* Decisions made
    - Not adopted: a launcher that spawns every DuckDB version as a sibling. Unsetting `VIRTUAL_ENV` on the two version-pinned children is the smaller fix
* Insights
    - While `VIRTUAL_ENV` points at the overlay, `uv run --with` ignores the requested package and runs the project interpreter










## 2026-10-21 - PREFLIGHT - COMPLETE (FAIL (fixable))

* Work completed
    - Preflight of the DuckDB 2.0 plan. First line of `memory-bank/active/.preflight-status` is `FAIL (fixable)`
* Decisions made
    - The plan changes before build. The shadow repair has to run on a leftover-`.wal` copy and on a folded copy. Folding first leaves the loud state unproven
* Insights
    - On 1.5.4, one row is enough for `EXPLAIN` of the unscoped cosine statement to contain `HNSW_INDEX_SCAN`. `uv run --with duckdb==2.0.0` layered 2.0.0 over `.venv` and left the project interpreter on 1.5.4. This `.venv` has no torch; the hashed freeze is present

## 2026-10-21 - PREFLIGHT - COMPLETE (FAIL (fixable))

* Work completed
    - Preflight of the revised DuckDB 2.0 plan. The plan was not edited. First line of `memory-bank/active/.preflight-status` is `FAIL (fixable)`
* Decisions made
    - The 2.0 ingest, embed, and semantic commands have to run as the overlay interpreter with `PYTHONPATH=skills/sr-search/src`. A nested `uv run` uses the project `.venv` and DuckDB 1.5.4
    - `make ci` is the sync that moves `.venv`. A failed gate restores the 1.5.4 lock and runs `make sync` before the next nightly job
* Insights
    - Measured: parent `uv run --with duckdb==2.0.0` is ephemeral 2.0.0; nested `uv run --no-sync --with duckdb==1.5.4` warns that the overlay `VIRTUAL_ENV` does not match `skills/sr-search/.venv` and runs 1.5.4 there. The project interpreter stayed 1.5.4. `import stockroom` is missing until `PYTHONPATH` includes `skills/sr-search/src`

## 2026-10-21 - PREFLIGHT - COMPLETE (FAIL (fixable))

* Work completed
    - Preflight of the second re-plan. The plan was left unchanged. First line of `memory-bank/active/.preflight-status` is `FAIL (fixable)`
* Decisions made
    - The repair phases have to see the loud state and the folded state before they repair. A healthy index that survives the kill is a failed phase
    - An observation hang and an `InternalException` both count as the loud state. A normal return does not
* Insights
    - Killing the writer when `warehouse.duckdb.wal` appears can land before the embeddings insert commits. Replay then rolls that insert back and the index stays whole

## 2026-10-21 - PREFLIGHT - COMPLETE (FAIL (fixable))

* Work completed
    - Preflight of the third re-plan. The plan was not edited. First line of `memory-bank/active/.preflight-status` is `FAIL (fixable)`
* Decisions made
    - The repair's embeddings count is the count after the killed commit, compared after the repair checkpoint and before the post-repair delete and insert
    - A probe that cannot open the file fails the phase. Loud requires that the probe opened the database and then hung or raised
    - The patch repeat accepts only final `2.0.N` versions. The child is `uv run --no-sync --with duckdb==<version>`
* Insights
    - Measured: a second open of a DuckDB file this process still holds raises `IOException` `Could not set lock`. After close, the open succeeds
    - Measured: `EXPLAIN` of a `?` statement without the bound value raises `InvalidInputException`
    - Measured: PyPI's latest duckdb is `2.0.0`. `2.0.0.dev*` uploads are published and sort after `2.0.0` as strings
    - `uv` 0.12.22 `uv run` syncs inexactly unless `--exact`. Torch is absent from the project `.venv`

## 2026-10-21 - PREFLIGHT - COMPLETE (FAIL (fixable))

* Work completed
    - Preflight of the fourth re-plan. The plan was not edited. First line of `memory-bank/active/.preflight-status` is `FAIL (fixable)`
* Decisions made
    - The patch-repeat child has to be started with `VIRTUAL_ENV` unset. A nested `uv run --with` from inside the 2.0 overlay runs the project interpreter, DuckDB 1.5.4
* Insights
    - Measured: the parent overlay is ephemeral 2.0.0 and its `VIRTUAL_ENV` is that prefix. Unsetting `VIRTUAL_ENV` makes `uv run --no-sync --with duckdb==2.0.0` select 2.0.0. The project interpreter stayed 1.5.4
    - Measured: one HNSW insert leaves a 1701-byte wal after the index is checkpointed. A 4KB threshold set before that checkpoint leaves no wal
    - Measured: `pragma_hnsw_index_info()` takes no arguments on 1.5.4 and 2.0.0. The indexed-row count is the `count` column

## 2026-10-21 - PREFLIGHT - ABORTED

* Work completed
    - A preflight of the plan at `3ccba40` was aborted before it wrote `.preflight-status`
    - It left two untracked SumMem notes
* Decisions made
    - None. The plan was not edited
* Insights
    - Measured, and not yet folded into the plan: from inside `uv run --with duckdb==2.0.0`, a nested `uv run --no-sync --with duckdb==VERSION` selects `VERSION` even when `VIRTUAL_ENV` is inherited. Unsetting `VIRTUAL_ENV` is not what makes `--with` take effect
    - Measured: on DuckDB 2.0.0, `EXPLAIN` of the unscoped cosine query contains `HNSW` in the line `HNSW Index: embeddings_vector_hnsw`. The operator title is `Hnsw Index Scan`, which does not itself contain `HNSW`. A case-sensitive `HNSW` check passes on 1.5.4 and 2.0.0

