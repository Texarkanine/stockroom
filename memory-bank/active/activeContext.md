# Active Context

## Current Task: warehouse-check-review-wording
**Phase:** PLAN - COMPLETE

## What Was Done

- First preflight failed with three fixable findings. The plan now matches them.
- The restore renames only from a stopped `swapped` record. `running` and busy `linked` wait. A free `linked` record gets one new session. `overrun` uses the backup-aside recovery.
- Rehearsal is limited to an eligible warehouse, and the replacement is at least one day later.
- The dismiss reply is limited to a version-1 `started` object.
- No new test. No new command. No change to the check state machine or to `os.fsync`.

## Next Step

- Preflight the revised plan.
