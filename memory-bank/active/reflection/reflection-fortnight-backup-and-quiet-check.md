---
task_id: fortnight-backup-and-quiet-check
date: 2026-10-28
complexity_level: 2
---

# Reflection: Soak clock starts when the new warehouse is live

## Summary

The 14-day backup soak now starts when the record becomes `swapped`, not at phase B `started_at`. QA passed on the second run. The earlier reflection for this task id measured the soak from `started_at`; this rework replaces that.

## Requirements vs Outcome

The rework brief is in the code. `swapped_at` is stamped when status becomes `swapped`, including both resume branches, and the unlink reads only that field. A swapped record with no `swapped_at` is stamped on the stop path only when the backup and the live warehouse are different files, and that pass does not unlink. Homes with no backup or no live warehouse still start no child. The user guide and the lifecycle sentence match. The numbered restore steps are unchanged. Nothing was added that the plan left out except the shared file check `_distinct_backup`.

## Plan Accuracy

The four units and their order held. The file list was right; `lifecycle.md` was an advisory, not a planned file, and the second QA asked for the one sentence. The challenges that mattered were the ones in the plan: a missing stamp that never launches stays forever, and a stamp that also unlinks in the same pass removes the backup immediately. The surprise was in the tests. A deadline fixture whose `started_at` equals `swapped_at` stays green on the old predicate, so it does not prove the clock moved.

## Build & QA Observations

The red runs failed for the right reason: the old predicate still read `started_at`. The first QA failed only on names. Four retargeted tests still said `started_at` after their bodies checked `swapped_at`, and one of those names said the parent returns while the body asserted a launch. The three advisories were a unused parameter, one long docstring line, and the lifecycle sentence.

## Insights

### Technical
- A frozen clock makes phase B `started_at` and `swapped_at` equal. Only a second, later clock shows that the soak did not start at phase B.
- There is no fallback from a missing `swapped_at` to `started_at`. That fallback is the late-resume bug.

### Process
- Retargeting a test without renaming it leaves a name that contradicts the assertion. The plan said to retarget and did not say to rename, and QA was right to fail that.

### Million-Dollar Question

`swapped_at` on the record, written at the moment status becomes `swapped`, is the clock. The backfill for records that already say `swapped` without that field is the migration, not a second design. One file check shared by the parent and the stop path is enough. A single `keep` / `stamp` / `unlink` answer was considered and is not needed.
