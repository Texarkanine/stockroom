# Project Brief

## User Story

As a person whose warehouse has already been swapped, I want the pre-swap backup removed a fortnight after that swap, and I want session start to stop spawning a warehouse check once that home is finished and the backup is gone, so the machine does not keep a second copy of the old warehouse and does not import DuckDB or start a detached check on every later session.

Authoritative specs:

- [Issue 154](https://github.com/Texarkanine/stockroom/issues/154) — reclaim the swap backup a fortnight after the swap
- [Issue 155](https://github.com/Texarkanine/stockroom/issues/155), item 1 only — short-circuit a finished home

## Use-Case(s)

### Use-Case 1: Fortnight has passed

The check record is version 1 and `swapped`. `started_at` is at least 14 days ago. `warehouse.issue147-swap.duckdb` and `warehouse.duckdb` are both files and their inodes differ. The check pass unlinks the backup. The live warehouse bytes and `check.json` stay as they were.

### Use-Case 2: Finished home, backup already gone

`check_version` is 1, status is `swapped`, `already-new`, or `mismatch`, and the backup is not a file. The process the session-start hook runs returns without spawning a child and without importing DuckDB.

### Use-Case 3: Finished home, backup still present

Status is `swapped` (or another terminal status) and the backup file is still there. Session start still spawns the child, so the fortnight unlink can run.

### Use-Case 4: Home is not finished

Status is `linked`, `started`, `rehearsed`, or `skip`, the record is missing or unreadable, or `started_at` is missing. The backup stays. Session start still spawns the child.

## Requirements

1. In the check pass (`skills/sr-search/src/stockroom/check.py`), unlink `warehouse.issue147-swap.duckdb` only when all of the following hold:
   - The record's `check_version` is 1 and its status is `swapped`.
   - `started_at` is a number. This is the phase B clock, written at the start of the swap, not the backup file's modification time.
   - `now >= started_at + 14 * 86400`.
   - `warehouse.issue147-swap.duckdb` and `warehouse.duckdb` are both files, and their inode numbers differ.
2. Do that under the writer flock the pass already holds, and only on the `stop` path for `swapped`. A missing backup is a no-op. Do not rewrite `check.json`. Do not unlink any other name.
3. Leave the backup in place when status is `linked`, `started`, `rehearsed`, `skip`, `mismatch`, or `already-new`, when `started_at` is missing, or when the two inodes match.
4. Update the restore section in `docs/user-guide/troubleshooting/index.md`. Stockroom keeps that file for the fortnight. Putting the original back has to happen before then. A new session after the deadline can remove the file in the background.
5. The module the hook executes must not import DuckDB at import time. Using `stockroom.home.resolve_home` (stdlib) and the record file, return before `launch()` when all of the following hold:
   - `check_version` is 1
   - status is `swapped`, `already-new`, or `mismatch`
   - `warehouse.issue147-swap.duckdb` is not a file
6. Any other record, a missing or unreadable record, or a backup that is still present still calls `launch()`.
7. Do not delete or rename `check.json` in the short-circuit. Do not reimplement home resolution in the hook shell.
8. Until the later removal (out of scope), session start still starts this one short-lived interpreter. It does not start the child, and it does not import DuckDB, once the home is finished and the backup is gone.

## Constraints

1. Item 2 of issue 155 is out of scope: do not delete the check invocation, the check module, the swap-backup constant, or the restore procedure. Do not add `check-2.json`.
2. The fortnight unlink is not the short-circuit's job. Short-circuiting on `swapped` alone would skip the unlink.
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
8. `swapped` with the backup present: the parent still spawns the child.
9. `rehearsed`, `linked`, `started`, `skip`, or no record: the parent still spawns the child.
10. The parent path does not import DuckDB.
