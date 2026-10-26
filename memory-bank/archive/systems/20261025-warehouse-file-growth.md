---
task_id: warehouse-file-growth
complexity_level: 4
date: 2026-10-25
status: completed
---

# TASK ARCHIVE: Warehouse file growth

## SUMMARY

Stockroom warehouses stay near the size of the history they hold. The HNSW index and the `vss` extension are gone. The engine is DuckDB 2.0. A new warehouse is created from a frozen schema file in storage `v2.0.0` with zstd on `messages.text` and `tool_calls.tool_input`. An old warehouse is rehearsed, then at a later session start copied again, hard-linked to a backup name, and replaced. Session start launches that check and does not wait. `stockroom doctor` reports the storage facts and never writes.

Spec was [issue 147](https://github.com/Texarkanine/stockroom/issues/147), as amended by the operator. The issue kept HNSW and started the rewrite from a writer open. On 2026-10-21 the operator dropped the index. On 2026-10-22 the operator put the swap inside a two-phase check that session start launches, and ruled that released migration SQL stays as shipped.

Delivered as a Level 4 project across seven milestones (L3, L3, L3, L2, L3, L3, L2). No milestone was added or removed. Milestones 1–3 shipped on main as squash `0e1e62e` and as v3.0.0 (`c9fbcc4`). Milestones 4–7 are pull request 152.

## REQUIREMENTS

From the project brief, as amended while the milestones ran:

1. The HNSW index and `vss` leave the engine. Migration `0009` drops the index where it exists. The released `0003` stays as shipped. New warehouses never run it. Semantic search is exact.
2. New warehouses come from a frozen schema file at storage `v2.0.0`, with zstd on the two large columns. A warehouse below schema 3, which holds no rows, stops with an error that names the file and tells the user to move it aside.
3. The check runs in the background. Phase A rehearses a verified copy, records it, and deletes the copy. Phase B, at least a day later, copies again, hard-links the original to the backup name, and replaces the live file. Ingest, embed, the nightly job, readers, and doctor do not start it.
4. The storage upgrade stays outside `schema_version`. Populated tables are never rebuilt in place.
5. The swap runs only after a verified rehearsal of the same check version on that machine. The original is kept by a hard link, then `os.replace`. Stockroom never deletes the backup.
6. `stockroom doctor` reports file size, block use, reclaimable space, storage format, free disk, the check record, and the backup when one exists. The report never writes. This project adds no doctor fix.
7. The engine is DuckDB 2.0 (`>=2.0,<2.1`). No release carries that lock with a vector index or `vss`.
8. Every release stands alone. A user who skipped earlier releases of this project still gets a warehouse that migrates, or an error that says what to do.
9. Released migration SQL is immutable. Comments may change. One chain runs forever. New warehouses are created from the schema file and then migrate forward.

### Cross-milestone invariants (held throughout)

- A bug can cost time. It cannot cost data. The original is attached read-only. The rewrite holds the writer flock, skips when a `.wal` is present, and replaces the live path only with a copy that the same run built and verified.
- The link comes before the replace. A failed link never replaces the file. Filesystems that refuse hard links are out of scope.
- Free disk must cover twice the live-byte estimate plus 64 MiB, or the pass skips. The estimate is live data size, not the original file size.
- Backup names start with `warehouse.issue147-` and end with `.duckdb`. The swap backup is `warehouse.issue147-swap.duckdb`.
- The format boundary in this project is schema 9, which is also the head. A skip retries at the next session start and has no error state of its own.
- Doctor commands a user can discover never write.

## IMPLEMENTATION

### Milestone list

The checklist order was the execution order. The diagram allowed the doctor report to start after DuckDB 2.0, in parallel with the new-file work. It ran after the new-file milestone, in list order. Estimated levels held.

What changed in the list's meaning, without adding or removing a milestone:

- Milestone 1 first retired `0003`. The 2026-10-22 immutability ruling undid that. Milestone 3 restored the released SQL and name. Milestones 1–3 ship together, because a restored `0003` needs `vss` unless the schema-file path already exists.
- A first plan for milestone 3 edited released SQL and had the runner drop zstd. The operator rejected it before that build. The plan that ran restores history and creates new files from the schema.
- Milestone 6's preflight added a durable `linked` record between the hard link and `swapped`. The operator kept the earlier window open on 2026-10-24: `os.link` can return, and the process can die, with the record still `started` and the backup name already taken. An expired `started` entry does not finish that shape from directory entries.
- The check stayed one milestone. Splitting the rehearsal from the swap would have hidden the sibling-versus-resume bug until the second half.

- [x] **m1 — Drop the HNSW index and remove `vss` (L3)**
- [x] **m2 — Move the engine to DuckDB 2.0 (L3)**
- [x] **m3 — Restore released migrations; new warehouses from a frozen schema file (L3)**
- [x] **m4 — Doctor storage report (L2)**
- [x] **m5 — Verified newer-format copy (L3)**
- [x] **m6 — Check pass: rehearse, then swap (L3)**
- [x] **m7 — Start the check at session start (L2)**

### Sub-run summaries

#### m1 — Drop the HNSW index and remove `vss` (L3)

Migration `0009` runs `DROP INDEX IF EXISTS embeddings_vector_hnsw`. The engine loads no `vss`. Semantic search keeps the nearest chunk per message owner and cuts to the limit before it joins `messages`. A warehouse at schema 8, including one with a leftover `.wal` from a killed embed, migrates to the head, keeps every row, and has no index. The drop was proved on a copy of this machine's warehouse before the migration landed in the live checkout. The live migrate took 0.8 s on the measured copy and 0.9 s on the live file. QA passed with two advisories, neither blocking.

The landing was one script, run on a scratch copy and then on the checkout, with a byte diff between them. Ties at the cut distance are common in this history. Comparing two rankings means comparing owners strictly nearer than the cut, on several query vectors.

Milestone 1's comment-only rewrite of `0003` did not survive. Milestone 3 put the released file back. The comment edits to `0001` were allowed and stayed.

#### m2 — Move the engine to DuckDB 2.0 (L3)

The engine range is `>=2.0,<2.1`. Dependabot ignores duckdb `>=2.1.0` in the engine block. `scripts/shadow_duckdb_20.py` copies a real warehouse under the writer flock, checkpoints it under 2.0, checks every table both ways, then runs ingest, embed, and semantic. DuckDB 1.5.4 can still write that copy, and 2.0 still opens it after that. The script exited 0 on this machine before the lock landed, and again from a fresh clone after it landed. The operator's release gate passed on the personal Mac (Puck) on 2026-10-23 against `09ea4ae`: exit 0 in 43 s, and the copy stayed `v1.0.0+`.

Nanobind leaked-instance warnings at exit came from a logger filter left on a third-party logger for the life of the process. The filter is now scoped to the model load. The warning can still appear from a pytest process that imports torch next to the engine conftest. That is the test runner, not a product leak. QA passed with five advisories, none blocking. The 2.0 lock was the last change this milestone brought into the live checkout.

#### m3 — Restore released migrations; new warehouses from a frozen schema file (L3)

`0001` through `0008` match the latest release's SQL, comments aside. `0003_embeddings_hnsw_index.sql` is back under its own name. `make migrations-check` fails when a released migration's SQL changes. `schemas/schema_0009.sql` creates the version-9 tables, keys, and `session_token_usage` view, with no index and with zstd on the two large columns. `warehouse.open()` of a missing warehouse builds that file under a temp name at storage `v2.0.0`, fsyncs it, and renames it into place under the writer flock. A warehouse below schema 3 raises `WarehouseUnmigratableError` and nothing renames or deletes it.

`COPY FROM DATABASE` into a new `v2.0.0` file stored `messages.text` as `DICT_FSST`, so the copy path does not use it. View SQL rendered by DuckDB differs between a `v1.0.0` file and a `v2.0.0` file, so later catalog checks do not compare view text. On a file opened with a `.wal`, replayed rows show `persistent = false` and `Uncompressed`. A zstd check counts persistent segments only.

The new-warehouse path was proved on Puck at `ac20922`: ingest 22 s, embed 490 s, semantic 5 s, storage `v2.0.0+`, both large columns `ZSTD`, `vss` unloaded. A scratch ingest on this machine takes hours, which is why the run moved. QA passed on the first run with nine advisories, none blocking.

#### m4 — Doctor storage report (L2)

`stockroom doctor` probe prints file size, used blocks, free blocks, reclaimable bytes, storage format, free disk, and, when the backup file is present, its path and size. Reclaimable bytes are the file size minus the distinct persistent block ids. The command checks that the warehouse exists before it opens anything, and it does not create the stockroom home. Help uses `RawDescriptionHelpFormatter` so the phrase "free disk" survives argparse wrapping. QA passed with advisories and no build change. The check-record line waited for milestone 6.

#### m5 — Verified newer-format copy (L3)

`copy_warehouse` attaches the original read-only, builds `warehouse.copy.duckdb` from the schema file, migrates that sibling only through the original's schema version, replaces the copy's `schema_version` rows with the original's, and inserts the rows. A fresh read-only connection then requires multiset equality both ways and catalog equality. Catalog helpers open each file alone, because after `ATTACH` the catalog lists both databases. An empty zstd column has no data segment and does not fail. A populated large column must store persistent zstd. The original bytes stay unchanged. The builder does not replace the live file and does not delete a backup. QA passed with advisories and no build change.

#### m6 — Check pass: rehearse, then swap (L3)

`python -m stockroom.check` is the entry. It is not a `stockroom` subcommand. `entry` sets `SIGALRM` to 14400 seconds and installs no handler. `run_check` does not set the alarm. The record is `check.json` in the stockroom home, written by a temp file, fsync, and `os.replace`.

Phase A writes `started`, copies, records `rehearsed` with the measurements, and deletes the sibling. A second call inside 86400 seconds does not copy again. Phase B copies the warehouse as it is that day, hashes the original, `os.link`s it to `warehouse.issue147-swap.duckdb`, writes `linked`, fsyncs, and `os.replace`s the sibling onto `warehouse.duckdb`. When the backup hash matches, that same pass writes `swapped`. A failed link returns with the record still `started` and the warehouse bytes unchanged.

`linked` is finished before leftover cleanup. Matching inodes and a sibling mean replace and write `swapped` from the stored measurements. Differing inodes mean write `swapped` and then delete a stray sibling. A missing sibling leaves the record `linked`. A hash mismatch after the replace leaves `linked`. The next pass writes `swapped` from the inode split and does not hash again.

Skips cover a missing home, a missing warehouse, a wal, a read-only filesystem, schema below the format boundary, low disk (`2 * live_bytes + 64 MiB`), and a busy flock. A stored skip walks that ladder again. Already-new means storage `v2.0.0+` and no persistent non-zstd segment on the large columns. A schema-file warehouse and an empty warehouse are already new.

The window the operator kept open: a crash after `os.link` returns and before `linked` is durable stays `started`. An expired `started` entry does not replace the warehouse. The next `os.link` fails while the backup exists, so deleting only `check.json` does not make phase B succeed. Recovery is a person moving `warehouse.issue147-swap.duckdb` aside, then deleting the record.

Doctor prints one check fact: `running` inside the limit, `overrun` past it. The word `crash` is not printed. Troubleshooting gives four rename steps to put the backup back, and says stockroom does not delete it. QA passed on the first run. The engine suite recorded 1158 passed and 36 skipped, with coverage-collection left out so torch stayed installed. Dashboard JavaScript recorded 134 passed.

#### m7 — Start the check at session start (L2)

Both session-start hooks start `python -m stockroom.check` and return at once. The child is detached the way the dashboard is: a new session, standard streams discarded, parent does not wait. Cursor's `beforeSubmitPrompt` hook does not start the check. A test runs the launched entry point against a final record and proves it does not build. On a home with no warehouse, ingest builds one from the schema file, and the launched check records `already-new` and builds nothing. QA passed on the first review. The DuckDB import on the hook parent stayed an advisory.

### Key artifacts

- `skills/sr-search/src/stockroom/migrations/0009_*.sql` drops the index. `0003_embeddings_hnsw_index.sql` is the released file.
- `skills/sr-search/src/stockroom/schemas/schema_0009.sql` and `stockroom.storage` create new warehouses and copy old ones.
- `stockroom.check` rehearses and swaps. `stockroom.doctor` reports storage and the check line.
- `hooks/cursor-hooks.json` and `hooks/claude-hooks.json` launch the check at session start.
- `scripts/shadow_duckdb_20.py` is the DuckDB 2.0 proof.
- `docs/user-guide/troubleshooting/index.md` says how to put the backup back.
- `make migrations-check` keeps released SQL frozen.

### Design decisions of record

- **Drop the index.** Exact search on the measured warehouse returned the full limit. The index did not. `vss` leaves with it. A later project can add an index back with a new migration.
- **DuckDB 2.0 storage `v2.0.0`.** DuckDB before 2.0 cannot open a file 2.0 creates. Existing warehouses keep their tag until the swap.
- **Released SQL stays.** A later migration changes what an earlier one left on disk. New warehouses skip the released chain by being born from the schema file.
- **Two-phase check, not a writer-open rewrite.** Each machine records a verified rehearsal. A later session start swaps a fresh copy. Phase B copies that day's warehouse, because rows written since the rehearsal exist only in the old file.
- **Hard link, then replace.** The original stays under the backup name until a person deletes it.
- **`linked` between the link and `swapped`.** A crash after that record is durable finishes without copying again. The crash before that record is durable stays `started` and does not auto-finish.
- **Alarm in `entry` only.** A Python handler does not interrupt DuckDB. The process ends, and the OS releases the flock. `run_check` does not arm an alarm, so an in-process test cannot kill a pytest-xdist worker.
- **Finish-swap uses inodes.** File size is a weak sign that rows changed. A missing sibling with matching inodes leaves the record `linked`.

## TESTING

- **m1:** Child-process fixtures for the index, the killed embed, and the killed migrator. Live-copy proof before the migration commit. `make ci` on DuckDB 1.5.4. QA passed.
- **m2:** Engine suite on a 2.0 overlay with torch. Shadow script exit 0 on a copy of this machine's warehouse, then again from a fresh clone of the landed branch. Puck gate at `09ea4ae`, exit 0 in 43 s. QA passed.
- **m3:** Red/green per step. `make migrations-check` failed on the pre-restore tree and named only `0003`. Puck real-data ingest, embed, and semantic at `ac20922`. QA passed on the first run.
- **m4:** `make ci`: 1098 pytest passed, 39 skipped, 134 JavaScript tests. QA passed on the first run.
- **m5:** 22 storage tests, then the engine suite (1110 passed, 36 skipped), 134 JavaScript tests. Ruff, schema docs, released migrations, and REUSE passed. QA passed on the first run.
- **m6:** 1158 passed, 36 skipped, coverage-collection omitted so torch stayed. 134 JavaScript tests. QA passed on the first run.
- **m7:** Launch tests went red on `NotImplementedError`, then passed. Hook tests went red on the missing command token, then passed. QA passed on the first review.

Proof the brief required is in the milestone 5 and 6 tests: equality both ways, catalog equality, the original's SHA-256 matching the backup after a swap, fault injection around create, build, verify, link, and replace, and skips for low disk, a wal, a busy flock, and a read-only filesystem.

## SYSTEM STATE

What exists now that did not before:

- **No vector index and no `vss` in the engine.** Semantic search is one exact path. Migration `0009` drops an index an older warehouse still has.
- **DuckDB 2.0**, held below 2.1. New files and the copy use storage `v2.0.0`. DuckDB before 2.0 cannot open those files. An old warehouse keeps its storage tag until the swap.
- **A frozen schema file** at version 9. A missing warehouse is built from it, under a temp name, and renamed into place. It never runs `0001` through `0009`.
- **A verified copy** (`warehouse.copy.duckdb`) that the check deletes after a rehearsal and renames onto the live path during a swap.
- **One check record per machine** (`check.json`). Phase A records `rehearsed`. Phase B, a day later, records `linked` and then `swapped`. The original remains at `warehouse.issue147-swap.duckdb`.
- **Session start launches the check** on both harnesses and does not wait. `beforeSubmitPrompt` does not.
- **A doctor storage section** that reports size, blocks, reclaimable bytes, format, free disk, the check line, and the backup. It never writes.

End to end: a writer open of an old warehouse migrates it to the head and drops the index, and does not start the copy. Session start starts one detached check. The first ready pass rehearses and deletes the copy. A later session start, at least a day after that record, copies again, links the original to the backup name, and replaces the live file with the verified copy. A warehouse that is already `v2.0.0+` with zstd on both large columns is recorded `already-new` and left in place. A person puts the original back by renaming `warehouse.duckdb` aside and renaming the backup to `warehouse.duckdb`. Stockroom does not delete the backup.

### Acceptance criteria — met

1. No stockroom warehouse keeps a vector index after the upgrade, and the engine loads no `vss`. A leftover `.wal` from a killed embed still migrates with every row. ✔
2. Semantic search is exact. An unscoped top-k returns k rows when enough messages have embeddings. ✔
3. A new warehouse is `v2.0.0+` with zstd on the two large columns. ✔
4. An existing warehouse is copied, verified, and, after a recorded rehearsal, swapped. The original stays under the backup name. ✔
5. The original's bytes are unchanged by the rewrite. Stockroom has no path that deletes the backup. ✔
6. The fault and skip list has tests. ✔
7. No machine swaps before a verified rehearsal of the same check version at least one day earlier. ✔
8. Doctor reports the storage facts and the check, and the report never writes. ✔
9. The engine runs on DuckDB 2.0. The shadow gate passed on this machine and on Puck. ✔
10. A `v1.0.0+` warehouse at schema 3 to 8 migrates without an earlier release of this project. Below schema 3, the open stops and names the file. ✔
11. Released migration SQL matches the latest release, comments aside. A new warehouse is built from the schema file and loads no extension. ✔
12. A new install works. Ingest builds from the schema file, embed and semantic answer, and the check records `already-new`. ✔

Deliberate open window, accepted 2026-10-24: a crash after `os.link` returns and before `linked` is durable. The record stays `started`. The backup name is taken. The next link fails until a person moves that file aside and deletes `check.json`. The check does not finish that shape from directory entries.

## LESSONS LEARNED

- **Land the migration that removes an on-disk dependency before removing the capability.** Every state in between still opens, so an interruption cannot break a live install.
- **Released SQL is a record, not a draft.** The way to stop running it for new files is a schema file at a later version, not an edit to the shipped file.
- **A measurement in one storage configuration does not travel.** View SQL, zstd visibility, and `COPY FROM DATABASE` compression all changed when the file's storage version changed. An empty zstd column has no data segment.
- **Finish a `linked` record before deleting `warehouse.copy.duckdb`.** The sibling is the verified copy the resume renames into place.
- **File size does not decide the resume.** Finish-swap compares inodes. A hash mismatch on the same pass leaves `linked`. The next pass writes `swapped` because the inodes differ.
- **The alarm belongs in the process entry point.** `run_check` stays callable from a test worker. A handler does not interrupt a running DuckDB statement, so the alarm ends the process.
- **Directory `fsync` through a read-only open already runs on the personal Mac.** `create_warehouse` fsyncs the parent directory that way, and the Puck ingest that built a new warehouse completed.

## PROCESS IMPROVEMENTS

- **When the working tree is the live engine, make the landing one script and run it on a scratch copy first.** Back up the warehouse before that landing. After each commit, `stockroom shim ensure-env`, because the commit hook's exact sync removes torch. Skip `tests/test_coverage_collection.py` on a full local run for the same reason.
- **Let preflight reject the phase diagram before a test locks it in.** Milestone 6's two fixable preflights caught a skip that would not retry, an alarm fixture that would never sleep, and a cleanup that deleted the sibling the resume has to rename.
- **Time a short sample of a real ingest during planning.** The embed bound did not predict that a scratch ingest on this machine takes hours. The run moved to Puck before it was finished here.
- **The Mac gate is the personal Mac.** The work Mac is not a personal-project gate. A branch clone there runs the shadow script only, never `make shim`.
- **Judge a relock by package name, version, and source.** uv 0.12.22 rewrites the lock format on any relock, so a raw diff overstates the change.
- **A stub sentence that later steps own a module will still be there when those steps land.** Replace it in the step that lands the behavior. QA will see it. It does not block.

## TECHNICAL IMPROVEMENTS

- **A stdlib launcher in front of `entry` would keep the hook parent from importing DuckDB.** The pass would still be the same child. The launch that shipped is the small version: `python -m stockroom.check`, absent from `stockroom --help`.
- **The pre-linked crash window stays a manual recovery.** Move `warehouse.issue147-swap.duckdb` aside, then delete `check.json`. An automatic finish from those directory entries would replace a warehouse the overrun decision leaves alone.
- **An unreadable `check.json` stays unreadable.** Doctor reports that word. Treating the file as a missing record would start phase A and can reach a swap.

## NEXT STEPS

None for this project. Pull request 152 carries milestones 4–7. Its title stays `feat:` so release-please can cut the release. The three review notes on abnormal check records and directory `fsync` were answered on the pull request and left unchanged.

### Million-Dollar Question (across sub-runs)

The small shape held. Drop the index, keep the released chain, birth new files from a schema snapshot, and move an old file by a recorded rehearsal and a later hard-link swap. The check is one detached child in front of `entry`, not a subcommand and not a writer-open side effect. The windows that remain are the ones a person clears: the backup file, and a `started` record whose backup name was published before `linked` was durable.
