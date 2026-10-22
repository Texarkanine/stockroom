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

## 2026-10-21 - PREFLIGHT - COMPLETE (FAIL (fixable))

* Work completed
    - Preflight of the fifth re-plan. The plan was not edited. First line of `memory-bank/active/.preflight-status` is `FAIL (fixable)`
* Decisions made
    - The kill child has to flush its embeddings count before it waits. A pipe buffers `print`, so the parent never reaches SIGKILL
    - Embed runs with `--verbose`. The embeddings floor is the post-ingest count minus the orphan line, because ingest deletes embeddings for rewritten messages before that line exists
* Insights
    - Measured: `print` then sleep on a pipe is not readable after one second
    - Measured: a schema-1 file at storage `v1.0.0` migrates to version 8 and keeps `v1.0.0+` on 1.5.4 and 2.0.0
    - Measured: EXPLAIN contains `HNSW` on 2.0.0 via the line `HNSW Index: embeddings_vector_hnsw`
    - Measured: nested `uv run --with duckdb==VERSION` selects VERSION even when `VIRTUAL_ENV` is inherited
    - Recorded an advisory to run the synthetic kill and the live branches through one `reproduce()` function

## 2026-10-21 - PREFLIGHT - ABORTED

* Work completed
    - A preflight of the plan at `3ccba40` was aborted before it wrote `.preflight-status`
    - It left two untracked SumMem notes
* Decisions made
    - None. The plan was not edited
* Insights
    - Measured, and not yet folded into the plan: from inside `uv run --with duckdb==2.0.0`, a nested `uv run --no-sync --with duckdb==VERSION` selects `VERSION` even when `VIRTUAL_ENV` is inherited. Unsetting `VIRTUAL_ENV` is not what makes `--with` take effect
    - Measured: on DuckDB 2.0.0, `EXPLAIN` of the unscoped cosine query contains `HNSW` in the line `HNSW Index: embeddings_vector_hnsw`. The operator title is `Hnsw Index Scan`, which does not itself contain `HNSW`. A case-sensitive `HNSW` check passes on 1.5.4 and 2.0.0

## 2026-10-21 - PLAN (SIXTH RE-PLAN) - COMPLETE

* Work completed
    - Folded the fifth preflight's fixable findings and the aborted run's measurements into the plan
    - The kill child flushes its count. `read_count_line` has a 5-second deadline. Embed is `embed --verbose`, and the embeddings floor is the post-ingest count minus the orphan line
    - Synthetic and live branches call one `reproduce` function
* Decisions made
    - `--with` selects a DuckDB version the project environment does not already provide, whether or not `VIRTUAL_ENV` is set. While the lock is 1.5.4, `--project --with duckdb==1.5.4` runs the project interpreter
    - Ingest, embed, and semantic stay on `sys.executable` because that process has the torch install
    - Not adopted: letting `sessions`, `messages`, or `tool_calls` shrink. The Done line still requires no fewer rows
* Insights
    - The fifth re-plan treated a 1.5.4 `--with` that reused the project interpreter as "`VIRTUAL_ENV` makes `--with` ignore the request". Requesting 2.0.0 from that same parent selects 2.0.0 with `VIRTUAL_ENV` inherited. `duckdb==2.0.99` exits 1 and does not run 1.5.4
    - An unflushed `print` on a pipe was still buffered after one second, so the parent never reached SIGKILL

## 2026-10-21 - PREFLIGHT (SEVENTH RUN) - COMPLETE (FAIL (fixable))

* Work completed
    - Preflight of the sixth re-plan. The plan was not edited. First line of `memory-bank/active/.preflight-status` is `FAIL (fixable)`
* Decisions made
    - `reproduce` waits for the flushed embeddings count until the line arrives or the child exits. The 5-second deadline stays on the unit test where the child has already printed and is sleeping
* Insights
    - The same function budgets 180 seconds for one probe of the real index. The count line is printed only after the HNSW insert commits, so a 5-second read ends before SIGKILL on the 39 GiB copy

## 2026-10-21 - PLAN (SEVENTH RE-PLAN) - COMPLETE

* Work completed
    - `reproduce` waits 180 seconds for the flushed embeddings count, or until the child exits, and sends SIGKILL if there is no line. The 5-second deadline stays on the unit test of a child that has already printed
    - After SIGKILL, and before any fold, the four observation statements run in one child. Each prints a flushed line. The parent kills that child once, at the first hang
* Decisions made
    - Adopted both advisories. The fold stays behind the observation. The proof pass after repair is the same four statements with no kill
* Insights
    - A 5-second read is enough to catch an unflushed pipe and too short for the insert that prints the count on the 39 GiB copy

## 2026-10-21 - PREFLIGHT (EIGHTH RUN) - COMPLETE (PASS WITH ADVISORY)

* Work completed
    - Preflight of the seventh re-plan. The plan was not edited. First line of `memory-bank/active/.preflight-status` is `PASS WITH ADVISORY`
* Decisions made
    - Build may start. The advisories do not change the plan
    - The observation probe list should name only statements that started. A hang on the first cosine query is opened and hung, not blocked
    - Repair's index rebuild is not on the 180-second kill timer
* Insights
    - On this warehouse the loud cosine query hangs, so the other three observation statements never start. Synthetic files raise `InternalException` instead, and the step 3 `reproduce` test accepts `healthy` from DuckDB 1.5.4
    - The overlay pytest already planned before `uv lock` can assert `loud` and `folded` on two tiny files, which fails a bad protocol before the 39 GiB copy

## 2026-10-21 - BUILD - FAIL (plan deficiency)

* Work completed
    - Step 1: `test_schema_one_v1_file_migrates_to_head_and_keeps_storage_tag`. Step 2: `test_unscoped_semantic_plan_uses_hnsw`. Both pass on 1.5.4 with no production change, and the HNSW assertion fails on the same statement without `LIMIT`
    - Step 3: `scripts/shadow_duckdb_20.py` and 14 tests in `test_shadow_duckdb_20.py`, green on 1.5.4. `reproduce` returns `healthy` there
    - Step 4 synthetic section on DuckDB 2.0.0 passed: `loud` and `folded` on small files, and the repair restored both
    - Step 4.3: no later milestone's Done or Risks sentence differs on 2.0.0, so `milestones.md` is unchanged. Same on 2.0.0 as stated: the storage tag of new and existing files, `'latest'` leaving an old tag, a second connection with another storage setting failing (`ConnectionException`), zstd raising `BinderException` at `v1.0.0` and giving `ZSTD` at `v1.2.0`, zstd surviving `ADD COLUMN` on a `v2.0.0+` file, a row-removing delete with the index up leaking one index copy (23 to 33 used blocks) while a no-match delete does not, `COPY FROM DATABASE` keeping the index and storing text as `DICT_FSST`, and an interrupt during `CREATE INDEX` taking effect only after the build
    - Step 4.3: `docs/architecture/embeddings.md`, two `semantic.py` docstrings, and the scoped starvation test said VSS applies `WHERE` after the HNSW pick. 2.0.0 filters inside the index scan (`Filters: optional`). Rewrote the three statements without a version. The test fixture is now 4,096 identical outsiders. A mutation check showed that a naive `WHERE` on the HNSW `LIMIT` query passed the old 32-row test on 2.0.0 and fails the new one on both versions
    - Step 4 live run on a copy of this machine's warehouse (42,426,445,824 bytes): the copy, checkpoint equality (6 tables), ingest (no table shrank), `embed --verbose` (+962 rows, 0 orphans), the `v1.0.0+` tag, semantic search, the unscoped plan, the 1.5.4 writer, and the 2.0.0 re-read passed. Branch A returned `loud`, and the repair restored 133,794 = 133,794 rows with all four proof statements. Branch B failed: `expected folded, got healthy`
* Decisions made
    - Build stops as a plan deficiency. The 2.0 lock is not landed, step 5 did not start, and `pyproject.toml` and `uv.lock` are unchanged at 1.5.4. The live warehouse was not modified (mtime 03:34, same size, no `.wal`)
    - Adopted the first preflight advisory: only started statements are probes, and repair is not on the 180-second timer
    - Not adopted: the radical advisory's overlay pytest that asserts `loud` and `folded`. The script's synthetic gate already fails in seconds, before the copy
    - Deviation: the scoped starvation test fixture changed (see above). It keeps that regression guard working at the 2.0 pin
* Insights
    - `pragma_hnsw_index_info` count is far above the row count on this warehouse: the healthy baseline reads 280,901 against 133,793 rows on 1.5.4 and on 2.0.0. The origin of the extra entries is unknown: `PRAGMA hnsw_compact_index` leaves the count at 280,901. A drop, create, and checkpoint (21 s) gives 133,793 = 133,793. After the branch B fold it reads 280,901 against 133,794. The folded rule (index count below row count) cannot fire on a warehouse with embedding deletes. The fold is real: an HNSW top-3 search with the replayed row's own vector misses it while the row is in the table at exact distance 0
    - The same count premise is in the doctor milestone (index-coverage check) and in the replay-bug invariant ("count is lower than `count(*)`"). Synthetic files never had a delete, so they agreed with it
    - On the live copy the loud cosine query raised `InternalException` and the delete hung. The eighth preflight's note that the cosine query hangs there did not hold
    - The extra entries shorten HNSW results: the unscoped `LIMIT 100` query returned 40 to 65 rows over 10 queries on the copy, under 1.5.4 and 2.0.0. Compaction changed nothing. After a rebuild every query returned 100
    - Under 2.0.0, `stockroom embed` and `stockroom semantic` print nanobind leak warnings to stderr at exit. Ingest does not
    - `approx_memory_usage` is the in-memory index size: 16.8 MB (2.0.0) and 21.0 MB (1.5.4) for a 1,500-row index in a 9.2 MB file

## 2026-10-21 - BUILD - OPERATOR DECISIONS

* Decisions made
    - Operator: this milestone's shadow script detects the folded state by an HNSW lookup of the replayed row by its own vector, not by count against `count(*)`
    - Operator: a fold on today's warehouses cannot be reliably detected read-only, and that is now the working assumption for the doctor milestone's coverage check
    - Operator: HNSW results shortened by stale index entries must be fixed
* Insights
    - DuckDB 1.5.4's Python package is built with pybind11. 2.0.0 is built with nanobind, whose shutdown check prints the "leaked instances" warnings seen after `stockroom embed` and `stockroom semantic`
