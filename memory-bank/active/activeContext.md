# Active Context

## Current Task: warehouse-check-review-wording
**Phase:** PREFLIGHT - COMPLETE (FAIL (fixable), stopped)

## What Was Done

- Classified the review follow-up as Level 2 and wrote the plan.
- Preflight failed five times. Each failure was a new gap in the restore prose, not a repeat of the previous gap.
- The lifecycle sentence, the eligible-warehouse qualification, the dead schema-head deletion, and the version-1 dismiss reply have matched the code since the third preflight.
- The restore page has not. The fifth failure is: the rename is not "backup file present"; the file steps need the probe's `home` and `backup` paths; a 300-second stop collides with the hook timeout; `already-new` is storage `v2.0.0+` and a passing zstd check.
- No docs, no `doctor.py` edit, and no GitHub reply have been written. The check state machine and `os.fsync` are unchanged.

## Next Step

- Stop. The operator chooses whether to keep revising the prose ladder, add a read-only probe word, or narrow the page to the `swapped` rename only.
