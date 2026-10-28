---
task_id: fortnight-backup-and-quiet-check
complexity_level: 2
date: 2026-10-28
status: completed
---

# TASK ARCHIVE: Soak clock starts when the new warehouse is live

## SUMMARY

Session start reclaims `warehouse.issue147-swap.duckdb` 14 days after the new warehouse is the live file, and it skips the detached check when that check would leave the disk alone. The soak clock is `swapped_at`, stamped when the record becomes `swapped`. Phase B `started_at` stays the four-hour alarm. The first design used `started_at` for the soak. A `linked` record can sit with no age limit, and the pass that writes `swapped` returns before the unlink, so the next session could remove the backup with no soak on the new file. This rework closes that.

## REQUIREMENTS

1. Unlink the backup only when `swapped_at` is at least 14 days old, the backup and the live warehouse are both files, and their inodes differ. The pass that writes `swapped` does not unlink.
2. Stamp `swapped_at` from the injected clock at the end of phase B and in both `_finish_swap` writes. `started_at` is not a fallback.
3. A swapped record with no `swapped_at` is stamped on the stop path only when those two files differ, and that pass returns before the unlink. No backup, or no live warehouse, and the parent does not start a child.
4. The parent still starts a child for an unfinished version-1 home, and it still returns without importing DuckDB when the child would leave the disk alone.
5. The user guide counts the 14 days from when the new warehouse is in use. The numbered restore steps stay. A bool `swapped_at` is not a timestamp.

## IMPLEMENTATION

- `skills/sr-search/src/stockroom/check.py`: `_swap_backup_due` reads `swapped_at`. `_phase_b` and both `_finish_swap` writes set it to the injected `now`. `_stamp_swapped_at` backfills a missing or `None` value through `_write_outcome` and does not unlink. `_distinct_backup` is the shared file check. `OSError` from that check starts the child and, on the stop path, leaves the record. A bool is left in place and is not due.
- `skills/sr-search/tests/test_check.py`: deadline fixtures give the old predicate a young `started_at`, so they go red until the predicate reads `swapped_at`. The 15-day resume is the second pass of the failed-replace test and of `test_replace_that_lands_resumes_without_copying`.
- `docs/user-guide/troubleshooting/index.md` and `docs/architecture/lifecycle.md`: the 14 days start when the new warehouse is in use. One child starts to stamp an unstamped backup that is a different file.

The check still runs under the writer flock, in the child. The parent does not unlink and does not import DuckDB. The hook command is unchanged. Ingest, mtime, and newer rows stay out of the predicate. A later major version deletes the check. A second migration before that bumps `CHECK_VERSION` in this module. `check-2.json` stays out.

If `os.replace` lands and the `swapped` write does not, the record stays `linked`. The next pass stamps `swapped_at` at that later `now`. The new file has been live for the whole wait, and the backup stays 14 days from the write.

## TESTING

`tests/test_check.py`: 82 passed. Engine pytest: 1232 passed, 6 skipped, and 5 failed outside this change (dashboard `/tmp` versus `/private/tmp`, a stale root docs lock, and three Node 26 coverage tests). Those three pass with Node 22. Dashboard JavaScript: 134 passed under Node 22. Ruff check and format are clean.

QA failed the first run because four retargeted tests still said `started_at`, and one name said the parent returns while the body asserted a launch. The second run passed after the renames, the unused `_outcome` parameter was dropped, the module docstring was wrapped, and the lifecycle sentence was updated. `_stamp_swapped_at` still repeats the guard the plan asked for.

## LESSONS LEARNED

- A frozen phase B clock makes `started_at` and `swapped_at` equal. Only a second, later clock shows that the soak did not start at phase B.
- Falling back from a missing `swapped_at` to `started_at` is the late-resume bug. There is no fallback.
- A deadline fixture whose two clocks are equal stays green on the old predicate. It does not prove which field the predicate reads.
- `True` equals `1`. A bool `swapped_at` is left in place, and the backup stays. The writer stores `time.time()`.

## PROCESS IMPROVEMENTS

When a test is retargeted, rename it in the same change. The plan said to retarget these tests and did not say to rename them. QA was right to fail the names.

## TECHNICAL IMPROVEMENTS

`swapped_at` on the record, written when status becomes `swapped`, is the clock. The backfill for records that already say `swapped` without that field is the migration. One shared file check is enough. A single `keep` / `stamp` / `unlink` answer was considered and left out.

## NEXT STEPS

None for the check. Pull request 156 is the delivery. `memory-bank/active/` is archived before that merge.
