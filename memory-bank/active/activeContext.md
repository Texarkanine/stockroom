# Active Context

## Current Task: warehouse-check-review-wording
**Phase:** PREFLIGHT - COMPLETE (FAIL (fixable))

## What Was Done

- Second preflight failed on two fixable wording gaps. The plan now covers them.
- A busy `swapped` value waits. The check, not the reader, is the actor that can replace the live file while the record is `linked`.
- Probe words are values after `key:`. A `linked` value that stays `linked` is a stop, with no claim about which bytes are live.
- The day-later replacement still has to find the warehouse eligible. The dismiss reply says `next_action` returns `phase-a`, and readiness can still skip the copy.
- No new test. No new command. No change to the check state machine or to `os.fsync`.
- Third preflight failed on three fixable gaps: overrun with no backup, the second probe jumping to the rename, and padded probe values.

## Next Step

- Re-plan the three fixable findings. Do not build.
