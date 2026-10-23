# Progress

L4 milestone 3 of 7 for `warehouse-file-growth` ([issue 147](https://github.com/Texarkanine/stockroom/issues/147), as amended in `memory-bank/active/projectbrief.md`): restore every released migration as it shipped, and create new warehouses from a frozen schema file in DuckDB 2.0's storage format with zstd on `messages.text` and `tool_calls.tool_input`. `0001` to `0008` get their released SQL back (comments may differ), `0003_embeddings_hnsw_index.sql` returns under its own name, and a `make ci` and CI gate fails when a released migration's SQL differs from the latest release tag. A frozen version-9 schema file outside the migrations folder creates new warehouses at an explicit `v2.0.0` storage version, under a temp name renamed into place under the writer flock, with one `schema_version` row naming it, then migrates them forward. A test keeps it equal to the chain at version 9, apart from compression. A warehouse at schema 3 to 8 migrates to the head without `vss`; one below schema 3 stops with an error that names the file and says to move it aside. Old-file builders load `vss` only in a separate process. Docs and `memory-bank` describe the schema file and the immutability rule. The new-warehouse path runs once on this machine's real transcripts in a scratch home. Milestones 1 to 3 make the first release.

**Complexity:** Level 3

## 2026-10-22 - COMPLEXITY ANALYSIS - COMPLETE

* Work completed
    - Cleared the L4 preflight status file (its findings are folded into `milestones.md` and `projectbrief.md`)
    - Classified milestone 3, "Restore every released migration as it shipped and create new warehouses from a frozen schema file in DuckDB 2.0's storage format with ZSTD on messages.text and tool_calls.tool_input"
* Decisions made
    - Level 3, as the L4 re-plan estimated. Most of the restoration copies files back from `main`. The new code is the schema file and its equality test, the create path with temp-then-rename, the stop rule, and the immutability gate. All of it sits in the warehouse creation and migration subsystem

## 2026-10-22 - PLAN - COMPLETE

* Work completed
    - Wrote the Level 3 plan in `tasks.md`: 9 steps and 35 behaviours (G1 to G8 for the immutability gate, S1 to S10 for the schema file and builder, W1 to W8 for `open()` and the CLI, R1 to R7 for the restored chain, H1 and H2 for the shadow script)
    - Probed DuckDB 2.0.0 in the scratchpad (`m3/probe_released_chain.py`, `probe_unbound_checkpoint.py`, `probe_unbound_close.py`, `probe_rw_open_bytes.py`, `probe_gate_tokens.py`)
* Decisions made
    - The released chain for tests is built in a child process that loads `vss`; the pytest process reads those files without it
    - The floor stop (below schema 3) is in the warehouse chokepoint, with a new typed error; `apply_pending` is unchanged
    - A new warehouse is linked into place (`os.link`, then `os.unlink` of the temp name), so creation can never replace an existing file
    - The gate compares SQL tokens against the highest `v*` tag and also covers `schemas/`, because a schema file is frozen like a migration
    - Order: gate, schema-file path, create and stop, `migrated_con`, then the restoration (preflight advisory 8), so no commit needs the released `0003` for a new install
* Insights
    - DuckDB 2.0.0 without `vss`, on a file with the HNSW index: an explicit `CHECKPOINT` after an `ALTER`, `INSERT`, or `CREATE VIEW` raises `FatalException`, but a plain close checkpoints fine. The runner's `0004` to `0009`, a kill mid-chain, and a tiny `checkpoint_threshold` all reach 9 with every row. The engine runs no explicit `CHECKPOINT`, so only test code could trip it
    - DuckDB re-prints view SQL in a form that does not round-trip, so the schema file copies `0007`'s view text word for word
    - `embed` runs in one transaction, so a time-killed embed keeps nothing; a "bounded" real-data embed needs a smaller source, not a kill

## 2026-10-22 - PREFLIGHT - COMPLETE

* Work completed
    - Preflight (Level 2/3 checks) on the milestone 3 plan. First line of `.preflight-status`: `PASS WITH ADVISORY`
    - No TDD swap or strike was needed, and `tasks.md` is unchanged
    - Spot-check (scratchpad `preflight/probe_schema2_bytes.py`, DuckDB 2.0.0): `v1.0.0` files at schema 0, 1, and 2 keep the same SHA-256 after a plain read-write open and close, so W3's premise holds for all three parameters
* Decisions made
    - Nine advisories, none blocking. The main ones: the G2 to G8 temp repos need a git identity on CI runners; writer `open()` must call creation inside the flock-releasing `try` (add a test); new installs now depend on hard links (operator to confirm that the 2026-10-22 ruling covers creation); `test_shadow_duckdb_20.py` stays red between steps 5 and 6. Full list in `.preflight-status`
    - Radical-innovation advisory: build release-matrix fixtures with DuckDB 1.5.4 from each tag's migration blobs, so W6 proves "as any earlier release left it" with the real on-disk format
* Insights
    - Local `main` (5f31292) is one commit behind `v2.1.3` (bc46e2b). That commit changes only version files, so restoring from `main` and gating against the tag give the same migrations and tests

## 2026-10-23 - REVIEW (OPERATOR) - COMPLETE

* Work completed
    - Folded the operator's two rulings and the agent's handling of the other preflight advisories into `tasks.md` (now 36 behaviours: W9 added)
* Decisions made
    - Operator: a new warehouse goes into place with `os.rename` after a check under the writer flock, not a hard link, so new installs do not depend on hard links (advisory 5; advisory 4 no longer applies)
    - Operator: W6's schema 3 to 8 files are written by DuckDB 1.5.4 with its `vss`, from the packaged chain, in one `uv run --with duckdb==1.5.4` child per pytest worker (reduced radical innovation; no per-tag matrix)
    - Agent: advisories 1, 2, 3, 6, 7, and 9 adopted as written; advisory 8 accepted and noted for QA
* Insights
    - The first preflight run, on Fable 5.1, stopped on a usage-credit 429 before writing anything; the second, on Opus, completed

## 2026-10-23 - BUILD - IN-PROGRESS

* Work completed
    - Step 0: backed up the live warehouse under the writer flock with no `.wal` to `~/.local/share/stockroom/warehouse.issue147-pre-schema-file.duckdb` (42,435,358,720 bytes, copied in 314 s). SHA-256 of both files: `20894505a14298be273a2f2a2d03956b3e667025c5cb231513a87cc4265d6a2d`. The milestone 2 backup stays
    - Step 1: `scripts/check_released_migrations.py`, `make migrations-check` (in `make ci`), and a CI step with `fetch-depth: 0`. G1 to G8 pass. On the real repo it fails and names only `0003_embeddings_hnsw_index.sql` (missing since milestone 1); `0001`'s comment edits pass
    - Step 2: `src/stockroom/schemas/schema_0009.sql`, `stockroom.storage`, the worker's `build_chain` and `index_knn_delete`, and the conftest fixtures `released_chain`, `released_chain_file`, `released_chain_con`. S1 to S10 pass
* Decisions made
    - The build stays on `constrain-size-as-best-we-can` (milestones 1 to 3 share one pull request)
    - S1 builds its chain file at `STORAGE_VERSION`, not `v1.0.0`: see the insight below
    - `create_warehouse` also removes the temp file when the build raises, so a failed build leaves no temp name (S10 checks it); a killed build still leaves one for the next creation to remove
    - `released_chain_file` takes an optional `dest`, so later tests can place a copy at the warehouse path
* Insights
    - DuckDB 2.0.0: a `v1.0.0` file reloads the view's SQL with one fewer closing parenthesis than memory or a `v2.0.0` file shows for the same view. Table SQL and constraints match. Milestone 5's catalog check compares a `v1.0.0` original with a `v2.0.0` copy, so it must not compare view SQL text (SumMem note)
    - The full suite after steps 0 to 2: 1,070 passed, 37 skipped, 3 failed. The three failures are torch-gated `test_embed` tests, and they pass on a rerun after `stockroom shim ensure-env`. Cause, which predates this milestone: `test_coverage_collection` runs `make coverage-engine`, whose `sync` dependency is an exact `uv sync` that removes torch from this checkout while the suite runs. Whether a torch-gated test fails depends on xdist scheduling. So the final gate is `make ci` (which syncs first, so torch tests skip), then `ensure-env` and a separate run of the torch-gated tests (SumMem note)

## 2026-10-23 - BUILD - COMPLETE

* Work completed
    - Step 3: writer `open()` creates a missing warehouse through `storage.create_warehouse` inside the flock-releasing `try`; writer `open()` and `_migrate_under_lock` stop below schema 3 with `WarehouseUnmigratableError` (path, current, quoted `mv`); `stockroom migrate` prints it as one line. W1 to W5 and W9 pass; W2 expects one schema-file row
    - Step 4: `migrated_con` installs the schema file, then later migrations
    - Steps 5 and 6 (one commit): the released `0003` and its five goldens are back, byte-equal to `v2.1.3`; `0003_retired.sql` is gone; `0003` gained one comment paragraph; `0009_snapshot.json` (no index) is the head golden. The `0003` to `0009`, runner, and shadow tests use child-built chains; W6 runs on schema 3 to 8 files written by DuckDB 1.5.4 and its `vss` (the fixture requires the child's `duckdb 1.5.4` line). `make migrations-check` and `make schema-docs-check` pass on the real repo. The shadow script's `--synthetic` section passes
    - Step 7: architecture and contributor docs, `systemPatterns.md`, `techContext.md`; `make docs-build` (strict) passes
    - Step 8.1: `make ci` exit 0 (1,085 passed, 39 skipped; 134 JS; REUSE compliant). After `ensure-env`, the torch-gated modules: 111 passed, 2 skipped (the intended inverse skip)
    - Step 8.3: `stockroom migrate` reports schema 9 on the live warehouse. Its SHA-256 after the open is `20894505a14298be273a2f2a2d03956b3e667025c5cb231513a87cc4265d6a2d`, the same as the step 0 backup, and mtime and size are unchanged. Tag `v1.0.0+`, no index
    - Step 8.2 started here: a scratch ingest of this machine's transcripts reached 455 of 1,473 Cursor sessions in 11 minutes and was stopped (operator: it takes hours on this machine). Its warehouse, built by the new path, was `v2.0.0+` with one `(9, 'schema_0009.sql')` row, no index, no `vss`, and every persistent segment of both columns `ZSTD`. Scratch home deleted
    - The Puck runbook (in `activeContext.md`) was dry-run on the test fixtures with this checkout: ingest, the file check, `ensure-env`, embed (19 s), and semantic (rank-1 row, no `nanobind:` line) all passed
* Decisions made
    - Operator: step 8.2 runs on Puck (M5 Mac, smaller warehouse) by Tachi from a fresh clone of the pushed branch; the new-warehouse path has no platform-specific code
    - Build deviations are listed in `activeContext.md` ("Build decisions and deviations"); none changes the plan's behaviours
* Insights
    - A read-only open of a zstd file that has a `.wal` lists the replayed rows as `persistent = false` and `Uncompressed`. A zstd check must count persistent segments only, or run with no `.wal` (SumMem note; matters for milestones 4 and 6)
    - In `sh`, `time` is `/usr/bin/time` and cannot run a shell function; the runbook's `time sr …` needs an interactive zsh or bash

## 2026-10-23 - QA - COMPLETE (PASS)

* Work completed
    - Semantic review of the build (`86b8954..HEAD`) against the Level 3 plan, milestone 3's done list, and the brief. Checked the gate and its tests, `storage.py` and the schema file, the chokepoint changes, the restored migration and goldens (compared with `v2.1.3`), the child-built chain fixtures, the shadow script, the docs, and `systemPatterns` / `techContext`
    - Ran, with no sync, on the landed tree: `make migrations-check` and `make schema-docs-check`; `ruff check` and `ruff format --check` on the engine and `scripts/`; the 15 milestone modules (119 passed); and the full suite without `test_coverage_collection.py` (1,084 passed, 36 skipped). Torch was still importable afterwards
* Decisions made
    - PASS. Nine advisories are recorded in `tasks.md`, and none blocks. The one that must be closed before the pull request opens is the Puck real-data run (step 8.2), which the operator handed to Tachi. The others are small cleanups: three redundant constant or filename assertions (change-detector lines), duplicated test helpers, a conftest parameter that hides the `storage` module, and stale "old 0003" wording in `0009`'s header
* Insights
    - The full suite minus `test_coverage_collection.py` is a safe QA run in this live checkout: it leaves torch in `.venv`, and only that one test runs the exact sync that strips it
    - Post-QA cleanups (main session): `0009`'s header says "the released 0003" instead of "the old 0003" (`0009` is unreleased, and only a comment changed); the redundant `SCHEMA_FILE` name and version assertions in `test_storage.py` and the `0003` filename assertion in `test_migrate_runner.py` are removed (the bookkeeping row and the gate already cover them). Affected modules and `make migrations-check` pass. The duplicated test helpers and the `storage=` keyword stay: the suite repeats small helpers per module, and the keyword is the plan's fixture API

## 2026-10-23 - REFLECT - COMPLETE

* Work completed
    - Wrote `memory-bank/active/reflection/reflection-warehouse-file-growth-m3.md`
    - Reconciled the persistent files: `productContext.md` skipped (no change to users, use cases, or constraints); `systemPatterns.md` skipped (step 7 already set the released-SQL rule, schema-file creation, and the floor); `techContext.md` gained one Testing Process pointer (the pytest process never loads `vss`; released-chain test files come from the child-built fixtures)
* Decisions made
    - Milestone 3 stays open on the Puck real-data run (step 8.2); its result goes here when the operator relays it
* Insights
    - Recorded in the reflection: time a sample of any real-data gate during planning; a restoration's evidence is byte equality with the tag plus behaviour tests, not a pin added to make a test red
