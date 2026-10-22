# Project Brief

## User Story

As a stockroom user, I want the warehouse file to stay near the size of the history it holds, so that months of sessions do not fill the disk.

Spec: [issue 147](https://github.com/Texarkanine/stockroom/issues/147). That issue is the authority for decisions, proof, and acceptance, except where the operator's amendments in this brief replace it. The issue says the rewrite runs from the writer path. Instead, the session-start hook starts one background check, and no writer open starts it. On each machine the check first records a verified rehearsal, and a later session start swaps a fresh verified copy in (operator, 2026-10-22). The issue keeps HNSW. Instead, the operator's 2026-10-21 decision drops the index, which also removes the NumPy insert path, the index rebuild, the doctor index checks, and the doctor fix that the earlier plan built around it.

Drop the HNSW index (operator, 2026-10-21): "drop the index. we don't need it. The avg dev that stockroom's for, won't need it. Strip everything ABOUT the index, too, 'cept the migration that drops it, yeah? well and anything else needed to make the 'take us to 2.0.0 and not waste space' work." The decision followed measurements on copies of this machine's warehouse (133,793 vectors, 42.4 GB file):
- The index held about 147,000 entries that match no row. Compaction left them, and a rebuild removed them. Through the index, a top-100 search returned 37 to 65 rows.
- Exact search took 130 ms (median) on DuckDB 2.0.0 and always returned 100 rows.
- Dropping the index and checkpointing took 0.8 s and freed 37.4 GiB inside the 39.5 GiB file. A fresh copy of what remained was 506 MB, made in 5.2 s.
- Without `vss` loaded, DuckDB 1.5.4 and 2.0.0 open a file that has the index, even with a leftover `.wal` from a killed 1.5.4 embed. They keep every row and drop the index inside a transaction. So `vss` leaves the engine as well, and DuckDB 2.0.0's `vss` replay bug cannot reach a stockroom warehouse.

The door stays open both ways. A later project can add an index back with a new migration and a rebuild routine. This project does not.

Lifetime (operator, 2026-10-21): the migration chain (verified copy, the check with its swap, session-start launch) is a short-lived utility for about five installs, optimistically six: the operator's four machines and a few people he knows. It stays in the plugin for a month or two, until every install has updated through Cursor, and is then removed. It must be reliable for those installs over that time, not long-term durable or bulletproof. The data-safety constraints below still hold in full. The index removal, the DuckDB 2.0 move, the new file format, and the doctor report are durable.

DuckDB 2.0 (operator, 2026-10-21): the engine moves from DuckDB 1.5.4 to DuckDB 2.0, a long-term support line supported until at least October 2027 (the 1.5 line ends in March 2027). The one-time rewrite then targets the format stockroom keeps. The first release carries the index drop and the 2.0 move together; the index drop may ship alone before it. The release that carries the 2.0 move is a major version (operator, 2026-10-22), so its pull request title carries `!`. It ships after the operator runs a shadow test from a clone of the branch on his machines. New files and the copy use storage `v2.0.0`. The operator chose it over `v1.5.0`, which DuckDB 1.5.4 could still open. DuckDB before 2.0 cannot open a file 2.0 creates. [Announcement](https://duckdb.org/2026/10/21/announcing-duckdb-200).

Skipped releases (operator, 2026-10-21): this project ships over several releases, and users skip releases. Every release must stand alone. A user who arrives from any earlier stockroom release, with no release in between, gets a warehouse that opens, migrates forward, and works. No release may assume that the user ran an earlier release of this project. Every stockroom release so far pinned DuckDB 1.5.4, so existing warehouses are `v1.0.0+` files at schema versions 0 to 8, with the HNSW index from schema 3 on. Schema 0 is an empty file that a failed first open left behind.

## Use-Case(s)

### Search

`stockroom semantic` ranks every embedding exactly. An unscoped top-k returns k rows whenever at least k messages have embeddings. `--harness` and `--role` are equality scopes on the same exact path.

### Upgrade

The first writer or migrating-reader open after the update runs the migration that drops the index. Every row stays. This includes a warehouse that a killed 1.5.4 embed left with a `.wal`. No network access is needed, because nothing loads `vss`.

### New warehouse

A brand-new warehouse is created in DuckDB's newest storage format (tag `v2.0.0+` on DuckDB 2.0). `messages.text` and `tool_calls.tool_input` are created with `USING COMPRESSION zstd`.

### Existing warehouse

The session-start hook starts one background pass, detached, through an internal engine entry point. There is no new user-facing CLI command, and ingest, embed, and the nightly job do not start it. The hook arrives with a plugin update, so a machine that only receives releases runs the check without re-installing anything. The pass has two phases, recorded per machine in one check record (operator, 2026-10-22):
- Phase A, the rehearsal, builds a new file, verifies it, records `rehearsed` with the original's size, the copy's size, free disk at the start, and the build, verification, and lock-hold times, then deletes the temp file. It never swaps.
- Phase B runs at a later session start, at least one day after a `rehearsed` record of the same check version. It copies the warehouse again as it is that day, because rows written since the rehearsal exist only in the old file. It verifies that copy, hard-links the original to a backup name, and replaces the live file with the verified copy.

A release that changes the check version and keeps phase B off is the kill switch. With the index gone, the copy is small and fast: 288 MiB in under 6 s for this machine's data.

### Doctor

`stockroom doctor` reports file size, used and free blocks, a reclaimable estimate based on live data size, the storage format, free disk, the background check's last outcome and measurements, and, when a backup exists, that backup's path and size. The report never writes.

Doctor writes (operator, 2026-10-21): a user can run any discoverable doctor command with full confidence that nothing is written. Any doctor action that writes sits behind `stockroom doctor fix <name>` and runs only when the user names it. This project adds no doctor fix.

## Requirements

1. The HNSW index and the `vss` extension leave the engine. A migration drops the index where it exists, and migration `0003` no longer creates one. Nothing in the engine loads or installs `vss`. Semantic search is exact.
2. New warehouses use the newer storage format and ZSTD on `messages.text` and `tool_calls.tool_input`. ZSTD is asserted through the column's data segments in `pragma_storage_info` (`VARCHAR` or `JSON`) after a write, on a new-format file. Validity segments show `Uncompressed` or `Constant` even under zstd, and an empty table has no data segments. `duckdb_tables().sql` does not show the compression clause.
3. The check pass runs in the background, in the two phases above. The session-start hook starts it. Ingest, embed, the nightly job, and other writer opens do not. Swapped, mismatch, already new, a crash, and a time-limit overrun are final; `rehearsed` waits for phase B. A crash or an overrun leaves a started entry that doctor shows, and deleting the record file runs the check again. Skips (low disk, a wal, a busy flock, a read-only filesystem, a filesystem that refuses hard links, no warehouse yet, a warehouse below the schema head) build nothing and retry at the next session start. At the time limit the process ends itself, so the OS releases the flock. It records the result in a sidecar file under the stockroom home and deletes the temp file. `open_current()`, the dashboard, and `stockroom doctor` never start it.
4. The rewrite is a storage upgrade outside the schema-version chain. A skipped rewrite must not make `open_current()` readers treat the warehouse as behind head.
5. Populated tables are never rebuilt in place. ZSTD and the newer format are applied when creating a brand-new warehouse and when copying rows into the new file. They are not a migration that rebuilds `messages` or `tool_calls` inside an existing file. The index-drop migration removes an index and rebuilds no table.
6. The swap (hard-link the original to a backup name, then `os.replace` the verified temp file onto `warehouse.duckdb`) runs only in phase B, after a verified rehearsal of the same check version on that machine at least one day earlier. It copies the warehouse again at that time. It does not replay the rehearsal's deleted temp file.
7. `stockroom doctor` gains the storage report on its existing read-only fact path. No `compact` subcommand. No doctor fix in this project.
8. The engine moves to DuckDB 2.0, proven by a shadow test on a copy of a real warehouse. No release carries the 2.0 move with a vector index or `vss`.
9. Every release of this project works for a user who skipped any number of earlier releases. The check treats a warehouse as already new only when it has the newest storage tag and zstd on both columns.

## Constraints

The rewrite must never break a warehouse. A bug can cost time. It cannot cost data. A crash during embed, including a power loss, must leave every committed row in the warehouse.

1. The original is attached `READ_ONLY` and the rewrite never opens it for writing.
2. The rewrite holds the writer flock for the whole operation. It starts only when the original is fully checkpointed and has no `.wal` file. Otherwise it skips.
3. It builds a sibling temp file on the same filesystem. The builder closes it, and no temp `.wal` may remain, before verification.
4. Verification reopens the temp file in a fresh read-only connection and requires exact multiset equality of every table, both directions (`EXCEPT ALL`), and the same catalog (tables, columns, types, constraints, views, and `schema_version` rows). Any difference aborts.
5. The swap, when it is run, keeps the original by adding a name, not by copying it. Hard-link the original to a backup name, then `os.replace` the verified temp file. If the filesystem refuses hard links, skip. There is no copy-then-delete fallback.
6. Stockroom never deletes the original. It stays under the backup name until the user deletes it. `stockroom doctor` reports its path and size.
7. Free disk must cover the new file plus a margin, or the rewrite skips. The new file's size is estimated from live data size, not from the original's file size. A skipped or failed rewrite leaves the warehouse exactly as it was, and `doctor` says so.
8. A leftover temp file from a crash is deleted on the next run, even when the record is final. A pass reads the record and deletes anything only while it holds the writer flock. A pass that cannot take the flock does nothing. Cleanup never touches the original or the backup. A warehouse already in the new layout is a no-op.
9. The rewrite `fsync`s the new file and its directory before the replace. Readers who already have the old file open keep that inode until they reopen.
10. Rollback is renaming the backup back to `warehouse.duckdb`.
11. Backup names (operator, 2026-10-22): every warehouse backup that stockroom makes, or that a contributor makes while building this project, sits in the stockroom home under a name that starts with `warehouse.issue147-`, followed by its purpose, ending `.duckdb`. Milestone 2's pre-move copy on the operator's WSL machine is `warehouse.issue147-pre-duckdb2.duckdb`. The doctor milestone defines the swap backup's name inside this pattern. A later release may delete stockroom's backups when they are present. It matches only this pattern, so it never deletes a backup the user made, such as a `warehouse.duckdb.bak` or `warehouse-pre-backfill.duckdb.bak`.

Proof that must have tests:

- The original's SHA-256 before a swap equals the backup's SHA-256 after it.
- Fault injection after the temp file is created, during the build, during verification, after the hard link, and after the replace. In every case `warehouse.duckdb` opens and holds either the original content or the verified new content, and no data file is lost.
- Low disk, a `.wal` present, hard links refused, the flock busy, and a read-only filesystem each skip and leave the original untouched.
- An old-format (`v1.0.0+`) fixture warehouse with rows written at `0001` and again after migrating to head is rewritten and passes the equality checks. One fixture is enough: the check copies only a warehouse at the schema head and skips one below it, and lazy migration brings a skipped-release warehouse to head.
- A schema-8 warehouse that has the index and a leftover `.wal` from a killed embed migrates to head with every row and no index.

Out of scope:

- A `compact` subcommand, on `doctor` or elsewhere.
- Chasing the primary-key leak in code (duckdb#17778). The one-time rewrite reclaims what has already leaked.
- Adding a vector index back, quantizing vectors, tiering old history, or deleting old history.
- The NumPy insert path. The re-plan dropped it with the index. A later project may take it up for speed.
- [Issue 146](https://github.com/Texarkanine/stockroom/issues/146) (nightly `stockroom shim ensure-env`). It should ship first and this work does not depend on it.

`duckdb.connect(path, config={"storage_compatibility_version": "latest"})` does not upgrade an existing file. The conversion copies the warehouse table by table into a new file attached in the newest storage version, as the copy milestone describes. Plain `COPY FROM DATABASE` does not apply the zstd clauses: on DuckDB 2.0.0 it stored `messages.text` as `DICT_FSST`. DuckDB 2.0 reads `v1.0.0+` files and creates `v2.0.0+` files that DuckDB before 2.0 cannot open.

## Acceptance Criteria

1. After the upgrade, no stockroom warehouse has a vector index, and nothing in the engine loads `vss`. A warehouse that had the index keeps every row, including one with a leftover `.wal` from a killed embed.
2. Semantic search is exact. An unscoped top-k returns k rows when at least k messages have embeddings.
3. A new warehouse is created in the `v2.0.0+` format with ZSTD on `messages.text` and `tool_calls.tool_input`.
4. An existing warehouse is copied automatically, and the copy passes the equality and catalog checks above. The rehearsal's copy is verified and deleted. At a later session start a fresh copy is verified and swapped in, and the original stays under a backup name.
5. The original file's bytes are unchanged after a rewrite, and stockroom has no path that deletes the backup.
6. Every fault and skip in the proof list has a test.
7. No machine swaps before it has recorded a verified rehearsal of the same check version at least one day earlier.
8. `stockroom doctor` reports file size, used and free blocks, reclaimable space, storage format, free disk, the background check's last outcome and measurements, and the backup when one exists, and the report never writes.
9. The engine runs on DuckDB 2.0. A copy of a real warehouse survives a 2.0 open and checkpoint unchanged, then ingest and embed under 2.0. DuckDB 1.5.4 can still write to it afterwards, and 2.0 still opens it after that.
10. A `v1.0.0+` warehouse at any schema version from 0 to 8, as any earlier release left it, works with each release of this project, with no earlier release of this project installed first. A warehouse left mid-embed by a power loss still opens with all its rows.
