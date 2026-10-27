# Project Brief

## User Story

As a person whose warehouse has already been swapped, I want the pre-swap backup removed a fortnight after that swap, and I want session start to skip the detached check whenever that check would leave the disk alone, so the machine does not keep a second copy of the old warehouse and does not import DuckDB or start a child on sessions that have nothing to do.

Authoritative specs:

- [Issue 154](https://github.com/Texarkanine/stockroom/issues/154) — reclaim the swap backup a fortnight after the swap
- [Issue 155](https://github.com/Texarkanine/stockroom/issues/155), item 1 only — short-circuit a finished home

## Use-Case(s)

### Use-Case 1: Fortnight has passed

The check record is version 1 and `swapped`. `started_at` is at least 14 days ago. `warehouse.issue147-swap.duckdb` and `warehouse.duckdb` are both files and their inodes differ. The check pass unlinks the backup. The live warehouse bytes and `check.json` stay as they were.

### Use-Case 2: Finished home, backup already gone

`check_version` is 1, status is `swapped`, `already-new`, or `mismatch`, and the backup is not a file. The process the session-start hook runs returns without spawning a child and without importing DuckDB.

### Use-Case 3: Swapped backup is due

The record is version 1 and `swapped`. The backup and the live warehouse are both files, their inodes differ, `started_at` is a number, and the fortnight has elapsed. Session start spawns the child. The child unlinks the backup. The live warehouse bytes and `check.json` stay as they were.

### Use-Case 4: Swapped backup is not due

The record is version 1 and `swapped`, and the backup is a file, but the child would leave it alone: the fortnight is still ahead, `started_at` is missing, the live warehouse is not a file, or the inodes match. Session start returns without a child and without importing DuckDB. The backup stays.

### Use-Case 5: Other finished record

Status is `already-new` or `mismatch` at version 1, whether or not the backup name is a file. The cleanup does not unlink that name. Session start returns without a child.

### Use-Case 6: Home is not finished

Status is `linked`, `started`, `rehearsed`, or `skip`, the record is missing or unreadable, or `check_version` is not 1. Session start still spawns the child, so a migration that has not finished can still run.

## Requirements

1. In the check pass (`skills/sr-search/src/stockroom/check.py`), unlink `warehouse.issue147-swap.duckdb` only when all of the following hold:
   - The record's `check_version` is 1 and its status is `swapped`.
   - `started_at` is a number. This is the phase B clock, written at the start of the swap, not the backup file's modification time.
   - `now >= started_at + 14 * 86400`.
   - `warehouse.issue147-swap.duckdb` and `warehouse.duckdb` are both files, and their inode numbers differ.
2. Do that under the writer flock the pass already holds, and only on the `stop` path for `swapped`. A missing backup is a no-op. Do not rewrite `check.json`. Do not unlink any other name.
3. Leave the backup in place when status is `linked`, `started`, `rehearsed`, `skip`, `mismatch`, or `already-new`, when `started_at` is missing, or when the two inodes match.
4. Update the restore section in `docs/user-guide/troubleshooting/index.md`. Stockroom keeps that file for the fortnight. Putting the original back has to happen before then. A new session after the deadline can remove the file in the background.
5. The module the hook executes must not import DuckDB at import time. The hook command stays. Using `stockroom.home.resolve_home` (stdlib), the record file, and `stat` of the backup and the live warehouse, `main` calls `launch()` in exactly two cases:
   - The home is not a finished version-1 record. Missing, unreadable, a `check_version` other than 1, `skip`, `rehearsed`, `started`, and `linked` all launch.
   - `check_version` is 1, status is `swapped`, the backup is a file, `started_at` is a number, `now >= started_at + 14 * 86400`, the live warehouse is a file, and the two inode numbers differ.
6. `main` returns before `launch()` whenever the child would leave the disk alone:
   - Version 1 and `swapped`, `already-new`, or `mismatch`, and the backup is not a file.
   - Version 1 and `swapped`, the backup is a file, and the fortnight is still ahead, or `started_at` is missing, or the live warehouse is not a file, or the inodes match.
   - Version 1 and `already-new` or `mismatch`, even when the backup name is a file.
7. Do not delete or rename `check.json` in the short-circuit. Do not unlink from the parent. Do not reimplement home resolution in the hook shell. Do not edit the hook files.
8. Until the later removal (out of scope), session start still starts this one short-lived interpreter. It does not start the child, and it does not import DuckDB, when the child would leave the disk alone.

## Constraints

1. Item 2 of issue 155 is out of scope: do not delete the check invocation, the check module, the swap-backup constant, or the restore procedure. Do not add `check-2.json`.
2. The fortnight unlink is not the short-circuit's job. The parent launches when the unlink predicate is already true, and returns when that predicate is false.
3. Backup mtime, access time, newer rows, and ingest are not the reclaim predicate.
4. `started_at` on a `swapped` record is the phase B clock from the start of the swap.

## Acceptance Criteria

1. `swapped` and younger than a fortnight: the backup remains.
2. `swapped` at exactly `started_at + 14 * 86400`: the backup is unlinked, the live warehouse bytes are unchanged, and the record is unchanged.
3. Same inode: the backup name remains.
4. Missing `started_at`: the backup remains.
5. `linked`, `mismatch`, and `already-new`: the backup remains.
6. A second pass after the backup is gone: no error, record unchanged.
7. `swapped`, `already-new`, or `mismatch`, backup absent: the parent returns and does not spawn a child.
8. `swapped`, backup present, one second under a fortnight, inodes differ: the parent returns and does not spawn a child.
9. `swapped`, backup present, exactly `started_at + 14 * 86400`, inodes differ: the parent spawns the child.
10. `swapped`, backup present, fortnight elapsed, same inode: the parent returns and does not spawn a child.
11. `swapped`, backup present, `started_at` missing: the parent returns and does not spawn a child.
12. `swapped`, backup present, fortnight elapsed, live warehouse missing: the parent returns and does not spawn a child.
13. `already-new` or `mismatch`, backup present: the parent returns and does not spawn a child.
14. `rehearsed`, `linked`, `started`, `skip`, no record, an unreadable record, or a `check_version` other than 1: the parent spawns the child.
15. The parent path does not import DuckDB, including the return for a young swapped backup.
