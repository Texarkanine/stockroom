---
task_id: warehouse-file-growth
date: 2026-10-23
complexity_level: 3
---

# Reflection: Restore released migrations; new warehouses from a frozen schema file (warehouse-file-growth, milestone 3)

## Summary

Every migration that shipped in a release has its released SQL again: `0003_embeddings_hnsw_index.sql` is back under its own name, and its five goldens are byte-equal to `v2.1.3`. A gate in `make ci` and CI keeps released SQL frozen. New warehouses no longer run the chain. They are built from a frozen version-9 schema file at storage `v2.0.0`, with zstd on `messages.text` and `tool_calls.tool_input`, and renamed into place under the writer flock. A warehouse below schema 3 stops with an error that names the file and the fix. QA passed on its first run with nine advisories, none blocking. The real-data run passed on Puck at `ac20922` (2026-10-23): ingest 22s, embed 490s, semantic rank 1. Figures are in `progress.md`.

## Requirements vs Outcome

Delivered against milestone 3's done list:
- **Restored history:** the released `0003` SQL and the `0003`, `0004`, `0006`, `0007`, `0008` goldens match `v2.1.3`. `0003` gained one comment paragraph. `0003_retired.sql` is gone, and `0009_snapshot.json` (no index) is the head golden. The generated ERD is unchanged.
- **Gate:** `make migrations-check` (also a CI step with `fetch-depth: 0`) compares SQL tokens with the latest `vX.Y.Z` tag, for `migrations/` and `schemas/`. On the repo before the restore, it failed and named only the released `0003`.
- **Schema file and builder:** `stockroom.storage` and `schemas/schema_0009.sql`. S1 keeps the file equal to the chain at 9, apart from compression.
- **New and existing warehouses:**
  - Writer `open()` creates from the schema file, and creation refuses an existing file.
  - Schema 3 to 8 files that DuckDB 1.5.4 and its `vss` wrote migrate to the head without `vss` (W6).
  - Below schema 3, the open stops with `WarehouseUnmigratableError`. `stockroom migrate` prints that as one line with a working quoted `mv`.
- **Builders:** old-format test files and the shadow script's synthetic warehouse are built in a child process that loads `vss`. The pytest process never loads it.
- **Docs:** the architecture and contributor docs, `systemPatterns.md`, and `techContext.md` are updated.

Delivered on Puck after this reflection was first written: the proof of the new-warehouse path on real transcripts (brief acceptance 12), at `ac20922`. Ingest exit 0 in 22s, embed exit 0 in 490s, semantic exit 0 in 5s with a rank-1 row. The scratch file was `v2.0.0+`, schema `(9, 'schema_0009.sql')`, no index, both large columns `ZSTD`, `vss` unloaded. The operator had moved the run to Puck because a scratch ingest on this machine takes hours. The partial run here had already shown those file properties before it was stopped, and the runbook had passed a dry run on the test fixtures. Full figures are in `progress.md`.

Added beyond the plan:
- `create_warehouse` also removes the temp file when the build raises.
- `released_chain_file` takes a `dest`.
- The shadow script's docstring says its synthetic section downloads `vss` once.

## Plan Accuracy

The plan's order held exactly: gate, schema file, create and stop, `migrated_con`, restore, shadow, docs, gates. So did its file list. No step needed reordering. Preflight advisory 6 predicted the one red window: the shadow test was red between the restore and its own fix, so steps 5 and 6 shared a commit.

Surprises:
- **S1's storage version:** the plan compared the schema file with a `v1.0.0` chain file. A `v1.0.0` file reloads the view's SQL with one fewer `)`, so that comparison could never pass. The plan's technology validation had compared view text in a single storage configuration. Fix: the chain file is built at `STORAGE_VERSION`.
- **Golden tests stayed green before the restore:** the plan expected the `0003` to `0008` golden tests (R3) to fail first. They passed, because the edited goldens and the retired chain agreed with each other. The red evidence came from R1, R5, R6, and W6, and from the byte comparison with `v2.1.3`.
- **The real-data run's cost:** the plan bounded the embed at 60 minutes but did not time an ingest into a scratch home. On this machine, that ingest alone takes hours.

## Creative Phase Review

No creative phase ran for this milestone. Two operator rulings stood in for design decisions, and both held:
- **Rename after a checked existence test (instead of a hard link):** about ten lines, with `lexists` before the build and again before the rename, all under the flock. W9 and S8 to S10 pin it.
- **W6 files from DuckDB 1.5.4:** one `uv run --with duckdb==1.5.4` child per pytest worker built all six files on the first try. The fixture fails if the child does not report `duckdb 1.5.4`.

## Build & QA Observations

- **TDD:** red and green were clean in every step. Each new test failed for the reason the plan named, then passed.
- **The live checkout:** this was the main friction. Each commit's hook and each `make ci` remove torch, so `ensure-env` ran after every one. A bare full `pytest` here also removes torch midway: `test_coverage_collection` runs an exact sync. Three torch tests failed once for that reason, not because of this milestone.
- **QA:** no defects. QA flagged three change-detector lines and stale "old 0003" wording in `0009`, which were fixed after QA, plus duplicated test helpers, which were left as the suite's existing style. One of the change-detector lines was mine: I pinned the restored filename only so that R6 would fail before the restore.
- **Live safety:** the live warehouse was untouched apart from the planned `stockroom migrate` no-op. Its SHA-256 matched the morning backup before and after.

## Cross-Phase Analysis

- **Preflight paid off three times:**
  - Advisory 7 (copy the `0008` golden to `0009` before the restore) removed a golden-regeneration run.
  - Advisory 6 matched the red window exactly.
  - Advisory 3 (create inside the flock-releasing `try`) gave W9, which pins a failure mode the code had no other test for.
- **The one build surprise traces to planning:** the technology validation ran in one configuration, and the test plan then specified another (S1 at `v1.0.0`) without probing it.
- **The real-data gap traces to planning:** the plan estimated the embed but not the ingest, so the operator had to reroute step 8.2 during the build.

## Insights

### Technical
- **Storage versions and view SQL:** DuckDB 2.0.0 renders a view's SQL differently for a `v1.0.0` file than for memory or a `v2.0.0` file, while table SQL and constraints match. Milestone 5's catalog check, which compares a `v1.0.0` original with a `v2.0.0` copy, must not compare view text (SumMem).
- **`pragma_storage_info` and a `.wal`:** on a file opened with a `.wal`, the replayed rows show as `persistent = false` and `Uncompressed`. A zstd check, such as milestone 4's doctor report or milestone 6's "already new" test, must count persistent segments only, or run only when there is no `.wal` (SumMem).
- **Full suite in the live checkout:** `pytest --ignore=tests/test_coverage_collection.py` keeps torch installed (SumMem).

### Process
- **Real-data gates:** time a short sample of the real run during planning, for example 10 minutes of ingest, and extrapolate. Here, a sample would have moved step 8.2 to Puck before the build started.
- **Restoration evidence:** the evidence for a restoration is byte equality with the release tag plus behaviour tests. Adding an assertion only so a test fails first produces a change-detector.
