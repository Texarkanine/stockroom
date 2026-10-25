# Active Context

## Current Task: warehouse-check-review-wording
**Phase:** PLAN - COMPLETE

## What Was Done

- Fourth preflight failed on two fixable gaps. The plan now covers them.
- Every new probe is read before the wait branch. The reader does not keep the previous probe's words.
- The `busy` observation and the 300-second clock for the `linked` stop start when the one session starts.
- The dismiss reply also says `doctor probe` still raises. No code change.
- No new test. No new command. No change to the check state machine or to `os.fsync`.

## Next Step

- Preflight the revised plan.
