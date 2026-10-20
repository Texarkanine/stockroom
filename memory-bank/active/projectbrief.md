# Project Brief

## User Story

As a stockroom user, I want the warehouse file to stay near the size of the history it holds, so that months of sessions do not fill the disk.

Spec: [issue 147](https://github.com/Texarkanine/stockroom/issues/147). That issue is the authority for decisions, proof, and acceptance. This brief records them for the milestone plan.

## Use-Case(s)

### Nightly embed

A run that changes `embeddings` and checkpoints must not leave another full copy of the HNSW index allocated in the file.

### Nothing to embed

A run that does not modify `embeddings` does not drop or rebuild the index.

### Backlog embed

Vectors are inserted by scanning a NumPy array in one statement. `BgeEncoder.encode` may keep returning arrays. The writer also accepts lists from the test fake and converts them.

### New warehouse

A brand-new warehouse is created in DuckDB's newer storage format (`STORAGE_VERSION 'latest'`, tag `v1.5.0+`). `messages.text` and `tool_calls.tool_input` are created with `USING COMPRESSION zstd`.

### Existing warehouse

One background pass checks an old warehouse once. There is no new CLI command, and ingest and embed do not start it. The first release builds the new file, verifies it, records the result, deletes the temp file, and never swaps. Enabling the swap is a separate, explicit change and stays off until that later change. The swap copies the warehouse again that day, because rows written after the check exist only in the old file.

### Doctor

`stockroom doctor` reports file size, used and free blocks, a reclaimable estimate, the storage format, free disk, and, when a backup exists, that backup's path and size. It never writes.

## Requirements

1. The HNSW index stays. Writers that change `embeddings` drop it before writing and recreate it after. Skip both when the run writes nothing.
2. Embed inserts go through a NumPy scan in one statement.
3. New warehouses use the newer storage format and ZSTD on `messages.text` and `tool_calls.tool_input`. ZSTD is asserted through `pragma_storage_info` after a write, on a new-format file. `duckdb_tables().sql` does not show the compression clause.
4. The check-only pass runs once in the background, not from ingest, embed, or any other writer open. It records the result and deletes the temp file. `open_current()` and `stockroom doctor` never start it.
5. The rewrite is a storage upgrade outside the schema-version chain. A skipped rewrite must not make `open_current()` readers treat the warehouse as behind head.
6. Populated files are never altered in place. ZSTD and the newer format are applied when creating a brand-new warehouse and when copying rows into the new file. They are not a migration that rebuilds `messages` or `tool_calls` inside an existing file.
7. The first release is that one background check. The swap (hard-link the original to a backup name, then `os.replace` the verified temp file onto `warehouse.duckdb`) is a later explicit change. It copies the warehouse again at that time. It does not replay the deleted temp file.
8. `stockroom doctor` gains the storage report on its existing read-only fact path. No `compact` subcommand.

## Constraints

The rewrite must never break a warehouse. A bug can cost time. It cannot cost data.

1. The original is attached `READ_ONLY` and the rewrite never opens it for writing.
2. The rewrite holds the writer flock for the whole operation. It starts only when the original is fully checkpointed and has no `.wal` file. Otherwise it skips.
3. It builds a sibling temp file on the same filesystem. The builder closes it, and no temp `.wal` may remain, before verification.
4. Verification reopens the temp file in a fresh read-only connection and requires exact multiset equality of every table, both directions (`EXCEPT ALL`); the same catalog (tables, columns, types, constraints, views, and `schema_version` rows); and the HNSW index present and answering a query. Any difference aborts.
5. The swap, when it is run, keeps the original by adding a name, not by copying it. Hard-link the original to a backup name, then `os.replace` the verified temp file. If the filesystem refuses hard links, skip. There is no copy-then-delete fallback.
6. Stockroom never deletes the original. It stays under the backup name until the user deletes it. `stockroom doctor` reports its path and size.
7. Free disk must cover the new file plus a margin, or the rewrite skips. A skipped or failed rewrite leaves the warehouse exactly as it was, and `doctor` says so.
8. A leftover temp file from a crash is deleted on the next run. Cleanup never touches the original or the backup. A warehouse already in the new layout is a no-op.
9. The rewrite `fsync`s the new file and its directory before the replace. Readers who already have the old file open keep that inode until they reopen.
10. Rollback is renaming the backup back to `warehouse.duckdb`.

Proof that must have tests:

- The original's SHA-256 before a swap equals the backup's SHA-256 after it.
- Fault injection after the temp file is created, during the build, during verification, after the hard link, and after the replace. In every case `warehouse.duckdb` opens and holds either the original content or the verified new content, and no data file is lost.
- Low disk, a `.wal` present, hard links refused, the flock busy, and a read-only filesystem each skip and leave the original untouched.
- Fixture warehouses at every schema version from `0001` through head are migrated, then rewritten, then pass the equality checks.

Out of scope:

- A `compact` subcommand, on `doctor` or elsewhere.
- Chasing the primary-key leak in code (duckdb#17778). The one-time rewrite reclaims what has already leaked.
- Dropping HNSW, quantizing vectors, tiering old history, or deleting old history.
- [Issue 146](https://github.com/Texarkanine/stockroom/issues/146) (nightly `stockroom shim ensure-env`). It should ship first and this work does not depend on it.

`duckdb.connect(path, config={"storage_compatibility_version": "latest"})` does not upgrade an existing file. The conversion is `COPY FROM DATABASE` into a file attached with `STORAGE_VERSION 'latest'`. Every tagged stockroom release pins DuckDB 1.5.4, which can read the new format. DuckDB 1.4.5 cannot.

## Acceptance Criteria

1. Changing `embeddings` and checkpointing no longer grows the file by an index copy. A test runs several write-and-checkpoint cycles and bounds the file size.
2. Nights that embed nothing do not rebuild the index.
3. An embed of a few thousand chunks is faster than today's insert path on the same data. The test asserts the NumPy insert path against a fixture rather than timing it.
4. A new warehouse is created in the `v1.5.0+` format with ZSTD on `messages.text` and `tool_calls.tool_input`.
5. An existing warehouse is rewritten once, automatically, and passes the equality, catalog, and HNSW checks above.
6. The original file's bytes are unchanged after a rewrite, and stockroom has no path that deletes the backup.
7. Every fault and skip in the proof list has a test.
8. The first release is verify-only. The swap is a separate, explicit change.
9. `stockroom doctor` reports file size, used and free blocks, reclaimable space, storage format, free disk, and the backup when one exists, and it never writes.
