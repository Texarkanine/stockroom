# Active Context

## Current Task: Soak clock starts when the new warehouse is live
**Phase:** REFLECT COMPLETE

## What Was Done
- The 14-day unlink reads `swapped_at`. Phase B and both `_finish_swap` writes stamp it from the injected `now`.
- A swapped record with no `swapped_at` is stamped on the stop path only when the backup and the live warehouse are different files, and that pass returns before the unlink.
- The user guide says the backup stays 14 days after the new warehouse is the one in use. The numbered restore steps are unchanged.
- Reflection is in `memory-bank/active/reflection/reflection-fortnight-backup-and-quiet-check.md`. It replaces the earlier reflection, which measured the soak from `started_at`.

## Files
- `/Users/tex/git/stockroom/skills/sr-search/src/stockroom/check.py`
- `/Users/tex/git/stockroom/skills/sr-search/tests/test_check.py`
- `/Users/tex/git/stockroom/docs/user-guide/troubleshooting/index.md`
- `/Users/tex/git/stockroom/docs/architecture/lifecycle.md`

## Decisions
- Deadline fixtures set `started_at` to the run's `now` and `swapped_at` to the old start, so the previous predicate fails those tests.
- The 15-day failed-replace resume is the second pass of `test_failed_replace_resumes_from_linked`.
- `_distinct_backup` is the shared file check. A `keep` / `stamp` / `unlink` function was not added.

## Next Step
- Run `/niko-archive` to archive this task.
