# Task: warehouse-file-growth, milestone 4 (doctor storage report)

* Task ID: warehouse-file-growth-m4
* Complexity: Level 2
* Type: simple enhancement

`stockroom doctor probe` prints warehouse file size, used blocks, free blocks, a reclaimable estimate, the storage format, free disk, and, when `warehouse.issue147-swap.duckdb` is present in the stockroom home, that file's path and size. The report does not write. The check record's last outcome is milestone 6. This milestone does not print that line.

The reclaimable estimate is the warehouse file size minus the live-size estimate. The live-size estimate is the number of distinct persistent block ids from `pragma_storage_info`, times `block_size` from `pragma_database_size`. Free blocks are printed. Free blocks are not the reclaimable estimate.

The swap backup name is `warehouse.issue147-swap.duckdb`. A later milestone writes that file. This milestone only reports the file when the file is already there.

## Test Plan (TDD)

### Behaviors to Verify

- Missing warehouse: a resolved home that does not exist → `warehouse: absent`, `disk-free` is a positive integer, no `blocks-used`. The home directory, the warehouse file, and the lock file are absent after the call.
- File size: a warehouse file in a temp home → `warehouse-bytes` equals that file's `stat` size.
- Blocks: the same file → `blocks-used` and `blocks-free` equal `used_blocks` and `free_blocks` from `pragma_database_size`.
- Storage format: the same file → `storage` equals `duckdb_databases().tags['storage_version']`.
- Reclaimable: the same file → `reclaimable-bytes` equals `warehouse-bytes` minus the distinct persistent `block_id` count times `block_size`. The value is `>= 0`.
- Backup present: `warehouse.issue147-swap.duckdb` in the home → `backup` is that path and `backup-bytes` is that file's size.
- Backup absent: no such file → `backup: absent` and no `backup-bytes` line.
- Other names: `warehouse.duckdb.bak` in the home → `backup: absent`.
- Busy: the lock file is held with an exclusive flock → `warehouse: busy`, `warehouse-bytes` is present, the injected connect is not called, and probe does not raise.
- Below head: a DuckDB file whose `schema_version` is below `warehouse._latest_version()` → probe does not raise, does not change the file's bytes, does not change `schema_version`, and still prints `warehouse-bytes` and `disk-free`.
- Read-only open failure: the connect raises → `warehouse: unavailable`, `warehouse-bytes` and `disk-free` are present, and probe does not raise.
- Existing facts: `os`, `arch`, `gpu`, `torch`, `engine-dir`, `home`, and `home-source` are still present.
- Help: `stockroom doctor --help` names file size, free disk, and the backup.

### Test Infrastructure

- Framework: pytest
- Test location: `skills/sr-search/tests/`
- Conventions: in-process facts in `test_doctor.py` through `probe_facts`. Subprocess CLI tests in `test_doctor_cli.py`. Temp homes come from the `warehouse_home` fixture or `tmp_path` plus `STOCKROOM_HOME`. Tests do not use the live warehouse.
- New test files: none

## Implementation Plan

### 1. Storage facts on probe — executable

- Files: `skills/sr-search/src/stockroom/doctor.py`, `skills/sr-search/tests/test_doctor.py`

1. Stub tests: add empty test functions in `test_doctor.py` for the behaviors above, except the help behavior.
2. Stub interface: add `SWAP_BACKUP_FILENAME = "warehouse.issue147-swap.duckdb"` and `storage_facts(home, *, connect)` on `doctor`. `storage_facts` returns `list[tuple[str, str]]`. `probe_facts` gains no new parameters. `probe_facts` calls `storage_facts` with the home from `resolve_home`.
3. Write tests and run red: assert the behaviors. The happy-path file is built in `warehouse_home` by the existing writer open, then closed, before probe runs. The below-head file is a temp DuckDB file with `schema_version` below the head. The busy test holds `fcntl.flock` on `.warehouse.lock` and passes a connect that raises `AssertionError` if called.
4. Write code and run green:
    - Resolve the home with `resolve_home`. Do not call `home_dir`, `warehouse_path`, `lock_path`, `open`, or `open_current`.
    - `disk-free` comes from `shutil.disk_usage` on the home when the home exists, otherwise on the nearest existing parent.
    - Stat the warehouse file and the backup file. Do not create either file.
    - Busy means `.warehouse.lock` exists and a non-blocking exclusive `fcntl.flock` fails. Open that lock file with no `O_CREAT`. On busy, do not connect.
    - Otherwise connect read-only to the existing warehouse file. Read `pragma_database_size` (`used_blocks`, `free_blocks`, `block_size`). Read `storage_version` from `duckdb_databases().tags`. Read each table's `pragma_storage_info` and count distinct `block_id` where `persistent` is true.
    - Compare `migrate.current_version` with `warehouse._latest_version`. Below head: do not migrate, and still return the stat facts. Connection facts are included only when those reads succeed.
    - A connect or pragma failure returns `warehouse: unavailable` plus the stat facts. It does not raise.

### 2. Doctor help text — executable

- Files: `skills/sr-search/src/stockroom/doctor.py`, `skills/sr-search/tests/test_doctor_cli.py`

1. Stub tests: extend `test_help_documents_both_actions` with empty assertions for the new words, then fill them.
2. Stub interface: none. The parser help string already exists.
3. Write tests and run red: `--help` stdout contains `file size`, `free disk`, and `backup`.
4. Write code and run green: the probe sentence in `_build_parser` lists those facts.

### 3. Contributor probe line — prose/policy

- Files: `docs/contributing/preparation.md`
- No tests: prose/policy artifact

1. Change the `stockroom doctor probe` comment so the comment names the storage facts as well as the shim facts.
2. Leave `stockroom doctor smoke` as it is.

## Technology Validation

No new technology - validation not required.

Confirmed in this checkout on DuckDB 2.0: `pragma_database_size` has `block_size`, `total_blocks`, `used_blocks`, and `free_blocks`. `pragma_storage_info` takes a table name. `storage_version` is already read from `duckdb_databases().tags` in the engine tests.

## Dependencies

- Milestone 3 is on `v3.0.0`. The schema head is `warehouse._latest_version()`.
- Milestone 6 will write `warehouse.issue147-swap.duckdb` and will add the check-record line to this same probe section.
- The live checkout's commit hook removes torch. Restore torch with `stockroom shim ensure-env` after the last commit of a session. Tests for this milestone do not import torch.

## Challenges & Mitigations

- `home_dir` and `open_current` create the stockroom home or refuse a behind-head file. Doctor uses `resolve_home` and a read-only connect. The missing-home test asserts the directory was not created.
- `_flock` creates the lock file (`O_CREAT`). The busy check opens the lock only when the lock file exists, and uses `LOCK_NB`.
- A behind-head file can still hold the HNSW index. A pragma failure becomes `warehouse: unavailable` plus the stat facts. Probe does not raise.
- `pragma_storage_info` on a file with a `.wal` marks replayed rows `persistent = false`. The live-size count keeps persistent segments only.
- An ambient `doctor probe` in `test_doctor_cli.py` can see this machine's warehouse. New tests set a temp home. The existing key check stays a subset check and still expects exit 0.
- This checkout is the live engine. No test opens the live warehouse file.

## Pre-Mortem

- Doctor calls `open_current` and creates a home or migrates a file. The missing-home test and the below-head byte check fail that implementation. Those tests are in step 1.
- Reclaimable is implemented as free blocks times block size. The reclaimable test computes the expected value from distinct persistent block ids, so that implementation fails.
- The plan also prints the check-record line. That line is milestone 6. The behavior list has no check-record fact.

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Pre-Mortem complete
- [ ] Preflight
- [ ] Build
- [ ] QA
