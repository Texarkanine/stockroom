# Project Brief

## User Story

As a stockroom user, I want the warehouse file to stay near the size of the history it holds, so that months of sessions do not fill the disk.

Spec: [issue 147](https://github.com/Texarkanine/stockroom/issues/147). That issue is the authority for decisions, proof, and acceptance, except where the operator's 2026-10-20 amendments in this brief replace it. The issue says the rewrite runs from the writer path. Instead, the session-start hook starts one background check, no writer open starts it, and the first release does not swap. This brief records the decisions for the milestone plan.

Lifetime (operator, 2026-10-21): the migration chain (verified copy, check, session-start launch, swap) is a short-lived utility for about five installs, optimistically six: the operator's four machines and a few people he knows. It stays in the plugin for a month or two, until every install has updated through Cursor, and is then removed. It must be reliable for those installs over that time, not long-term durable or bulletproof. The data-safety constraints below still hold in full. The new file format, NumPy inserts, HNSW rebuild, and doctor report are durable.

DuckDB 2.0 first (operator, 2026-10-21): before the format work, the engine moves from DuckDB 1.5.4 to DuckDB 2.0, a long-term support line supported until at least October 2027 (the 1.5 line ends in March 2027). The one-time rewrite then targets the format stockroom keeps. There is no 2.0-only release: the 2.0 move ships in one release together with the size work, after the operator runs a shadow test from a clone of the branch on his machines. New files and the copy use storage `v2.0.0`. The operator chose it over `v1.5.0`, which DuckDB 1.5.4 could still open. DuckDB before 2.0 cannot open a file 2.0 creates. [Announcement](https://duckdb.org/2026/10/21/announcing-duckdb-200).

Skipped releases (operator, 2026-10-21): this project ships in one release, then a later release turns the swap on, and users skip releases. Every release must stand alone. A user who arrives from any earlier stockroom release, with no release in between, gets a warehouse that opens, migrates forward, and works. No release may assume that the user ran an earlier release of this project. Every stockroom release so far pinned DuckDB 1.5.4, so existing warehouses are `v1.0.0+` files at schema versions 0 to 8. Schema 0 is an empty file that a failed first open left behind.

## Use-Case(s)

### Nightly embed

A run that changes `embeddings` and checkpoints must not leave another full copy of the HNSW index counted in used blocks. The file may hold one free copy of that index until the next such run reclaims it. The run checkpoints once, after the index is rebuilt.

### Nothing to embed

A process that does not change `embeddings` does not drop or rebuild the index. A delete that matches nothing is not a change. A process that deletes embedding rows and inserts none still rebuilds before it exits.

### Backlog embed

Vectors are inserted by scanning a NumPy array in one statement. `BgeEncoder.encode` may keep returning arrays. The writer also accepts lists from the test fake and converts them.

### New warehouse

A brand-new warehouse is created in DuckDB's newest storage format (`STORAGE_VERSION 'latest'`, tag `v2.0.0+` on DuckDB 2.0). `messages.text` and `tool_calls.tool_input` are created with `USING COMPRESSION zstd`.

### Existing warehouse

The session-start hook starts one background pass, detached, through an internal engine entry point. It checks an old warehouse once. There is no new user-facing CLI command, and ingest, embed, and the nightly job do not start it. The hook arrives with a plugin update, so a machine that only receives releases runs the check without re-installing anything. The check is a measured rehearsal of the swap. It records the original's size, the copy's size, free disk at the start, and the build, verification, and lock-hold times. The swap release sets its free-disk margin and expected writer wait from those numbers as measured on the operator's machines. The first release builds the new file, verifies it, records the result, deletes the temp file, and never swaps. Enabling the swap is a separate, explicit change and stays off until that later change. The swap copies the warehouse again that day, because rows written after the check exist only in the old file.

### Doctor

`stockroom doctor` reports file size, used and free blocks, a reclaimable estimate based on live data size (free blocks alone miss the leaked index copies, which count as used), the storage format, free disk, the background check's last outcome and measurements, and, when a backup exists, that backup's path and size. It also names a leftover `.wal` and, when no `.wal` is present, an HNSW index that is missing or short of rows. The report never writes.

Doctor fixes (operator, 2026-10-21): a user can run any discoverable doctor command with full confidence that nothing is written. Every doctor action that writes sits behind `stockroom doctor fix <name>` and runs only when the user names it. The first fix is `stockroom doctor fix hnsw-rebuild`. It repairs the HNSW index after a DuckDB 2.0.0 bug. Replaying a `.wal` that holds inserts into `embeddings` while the index exists leaves the index broken while the `.wal` remains: semantic search hangs or errors, a statement that touches `embeddings` fails, and an explicit checkpoint fails. A writer that does not touch `embeddings` can then pass DuckDB's automatic checkpoint threshold, delete the `.wal`, and leave the index silently short of rows. The rows stay in the table. The fix drops the index when one exists, creates it when it is missing, and checkpoints. No code repairs the index automatically. A troubleshooting page documents both states and the fix.

Happy path (operator, 2026-10-21): about five installs, embed runs nightly to completion, and this rollout is a couple of days. Build for a finished embed. A power loss during that embed may leave the index missing or short of rows, and the user looks up the troubleshooting page. That same power loss must not empty the warehouse or delete its rows. The HNSW index is dropped before a process adds or removes embedding rows, and recreated once, after every such change, before that process exits. A second embedding delete after the recreate leaks a used copy of the index. A process that changes nothing does not rebuild.

## Requirements

1. The HNSW index stays. A process that adds or removes `embeddings` rows drops the index before those statements and recreates it before it exits. A delete that matches nothing is not a change. Skip the drop and recreate when the process changes nothing.
2. Embed inserts go through a NumPy scan in one statement.
3. New warehouses use the newer storage format and ZSTD on `messages.text` and `tool_calls.tool_input`. ZSTD is asserted through `pragma_storage_info` after a write, on a new-format file. `duckdb_tables().sql` does not show the compression clause.
4. The check-only pass runs once in the background. The session-start hook starts it. Ingest, embed, the nightly job, and other writer opens do not. Verified, mismatch, already new, a crash, and a time-limit overrun are final. A crash or an overrun leaves a started entry that doctor shows, and deleting the record file runs the check again. Skips (low disk, a wal, a busy flock, a read-only filesystem, no warehouse yet, a warehouse below the schema head) build nothing and retry at the next session start. At the time limit the process ends itself, so the OS releases the flock. It records the result in a sidecar file under the stockroom home and deletes the temp file. `open_current()`, the dashboard, and `stockroom doctor` never start it.
5. The rewrite is a storage upgrade outside the schema-version chain. A skipped rewrite must not make `open_current()` readers treat the warehouse as behind head.
6. Populated files are never altered in place. ZSTD and the newer format are applied when creating a brand-new warehouse and when copying rows into the new file. They are not a migration that rebuilds `messages` or `tool_calls` inside an existing file.
7. The first release of this project runs that one background check and never swaps. The swap (hard-link the original to a backup name, then `os.replace` the verified temp file onto `warehouse.duckdb`) is a later explicit change. It copies the warehouse again at that time. It does not replay the deleted temp file.
8. `stockroom doctor` gains the storage report on its existing read-only fact path. No `compact` subcommand. Doctor writes only through `stockroom doctor fix <name>`. Its first fix, `hnsw-rebuild`, rebuilds the HNSW index under the writer flock. Doctor names that fix for a leftover `.wal` and for an index that is missing or short of rows.
9. The engine moves to DuckDB 2.0 first, proven by a shadow test on a copy of a real warehouse. No release carries the 2.0 move without the new-file format and the HNSW rebuild.
10. Every release of this project works for a user who skipped any number of earlier releases. The check treats a warehouse as already new only when it has the newest storage tag and zstd on both columns.

## Constraints

The rewrite must never break a warehouse. A bug can cost time. It cannot cost data. A crash during embed, including a power loss, may leave the HNSW index missing or short of rows. It must leave every row in the warehouse. The user recovers search from the troubleshooting page.

1. The original is attached `READ_ONLY` and the rewrite never opens it for writing.
2. The rewrite holds the writer flock for the whole operation. It starts only when the original is fully checkpointed and has no `.wal` file. Otherwise it skips.
3. It builds a sibling temp file on the same filesystem. The builder closes it, and no temp `.wal` may remain, before verification.
4. Verification reopens the temp file in a fresh read-only connection and requires exact multiset equality of every table, both directions (`EXCEPT ALL`); the same catalog (tables, columns, types, constraints, views, and `schema_version` rows); and the HNSW index present and answering a query. Any difference aborts.
5. The swap, when it is run, keeps the original by adding a name, not by copying it. Hard-link the original to a backup name, then `os.replace` the verified temp file. If the filesystem refuses hard links, skip. There is no copy-then-delete fallback.
6. Stockroom never deletes the original. It stays under the backup name until the user deletes it. `stockroom doctor` reports its path and size.
7. Free disk must cover the new file plus a margin, or the rewrite skips. The new file's size is estimated from live data size, not from the original's file size. A skipped or failed rewrite leaves the warehouse exactly as it was, and `doctor` says so.
8. A leftover temp file from a crash is deleted on the next run, even when the record is final. A pass reads the record and deletes anything only while it holds the writer flock. A pass that cannot take the flock does nothing. Cleanup never touches the original or the backup. A warehouse already in the new layout is a no-op.
9. The rewrite `fsync`s the new file and its directory before the replace. Readers who already have the old file open keep that inode until they reopen.
10. Rollback is renaming the backup back to `warehouse.duckdb`.

Proof that must have tests:

- The original's SHA-256 before a swap equals the backup's SHA-256 after it.
- Fault injection after the temp file is created, during the build, during verification, after the hard link, and after the replace. In every case `warehouse.duckdb` opens and holds either the original content or the verified new content, and no data file is lost.
- Low disk, a `.wal` present, hard links refused, the flock busy, and a read-only filesystem each skip and leave the original untouched.
- An old-format (`v1.0.0+`) fixture warehouse with rows written at `0001` and again after migrating to head is rewritten and passes the equality checks. One fixture is enough: the check copies only a warehouse at the schema head and skips one below it, and lazy migration brings a skipped-release warehouse to head.

Out of scope:

- A `compact` subcommand, on `doctor` or elsewhere.
- Chasing the primary-key leak in code (duckdb#17778). The one-time rewrite reclaims what has already leaked.
- Dropping HNSW, quantizing vectors, tiering old history, or deleting old history.
- [Issue 146](https://github.com/Texarkanine/stockroom/issues/146) (nightly `stockroom shim ensure-env`). It should ship first and this work does not depend on it.

`duckdb.connect(path, config={"storage_compatibility_version": "latest"})` does not upgrade an existing file. The conversion copies the warehouse table by table into a new file attached in the newest storage version, as the copy milestone describes. Plain `COPY FROM DATABASE` does not apply the zstd clauses. Every tagged stockroom release so far pins DuckDB 1.5.4. This project moves the engine to DuckDB 2.0, which reads `v1.0.0+` files and creates `v2.0.0+` files that DuckDB before 2.0 cannot open. These DuckDB facts were measured on 1.5.4; the DuckDB 2.0 milestone re-measures them.

## Acceptance Criteria

1. Changing `embeddings` and checkpointing, including a process that deletes rows and exits without inserting, does not add another index copy to used blocks. The file may sit one index above the start for a cycle; the next cycle reclaims that free copy. A test runs several change-and-exit cycles and, on every cycle, asserts used blocks or a high-water file size of one index over the start. It does not require a cycle's file to be no larger than the previous cycle. The skip is a process that did not change `embeddings`. A process that deletes embedding rows twice recreates once, after both deletes. A recreate between the two deletes fails the test.
2. A process that does not change `embeddings` does not rebuild the index. A process that deletes embedding rows and inserts none still rebuilds before it exits.
3. An embed of a few thousand chunks is faster than today's insert path on the same data. The test asserts the NumPy insert path against a fixture rather than timing it.
4. A new warehouse is created in the `v2.0.0+` format with ZSTD on `messages.text` and `tool_calls.tool_input`.
5. An existing warehouse is copied once, automatically, and the copy passes the equality, catalog, and HNSW checks above. In this project the copy is verified and deleted, not swapped in.
6. The original file's bytes are unchanged after a rewrite, and stockroom has no path that deletes the backup.
7. Every fault and skip in the proof list has a test.
8. The first release is verify-only. The swap is a separate, explicit change.
9. `stockroom doctor` reports file size, used and free blocks, reclaimable space, storage format, free disk, the background check's last outcome and measurements, the backup when one exists, a leftover `.wal`, and an HNSW index that is missing or short of rows, and the report never writes.
10. The engine runs on DuckDB 2.0. A copy of a real warehouse survives a 2.0 open and checkpoint unchanged, then ingest and embed under 2.0. DuckDB 1.5.4 can still write to it afterwards, and 2.0 still opens it after that.
11. A `v1.0.0+` warehouse at any schema version from 0 to 8, as any earlier release left it, works with each release of this project, with no earlier release of this project installed first. A warehouse left mid-embed by a power loss still opens with its rows. Search may miss rows until the fix in acceptance 12.
12. On a warehouse whose HNSW index the DuckDB 2.0.0 replay bug broke, either with the `.wal` still present or after the log has been folded and the index is short of rows, `stockroom doctor` names `stockroom doctor fix hnsw-rebuild`. After the fix, semantic search, ingest, and embed work again, the index count equals the row count, and no row changed. The rows were present before the fix.
