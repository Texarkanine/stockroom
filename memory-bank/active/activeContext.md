# Active Context

## Current Task: warehouse-file-growth
**Phase:** PREFLIGHT - COMPLETE (PASS WITH ADVISORY), post-preflight fixes folded in

## What Was Done
- Confirmed intent: implement [issue 147](https://github.com/Texarkanine/stockroom/issues/147) as written
- Classified Level 4
- Generated the milestone list (7 milestones) in `memory-bank/active/milestones.md`
- Preflight validated the original list (PASS WITH ADVISORY)
- Operator review: the check runs once in the background, records the result, deletes the temp file, and does not swap. Ingest and embed do not start it. The first release exists so other machines can prove a real warehouse before any swap. The swap stays off and, when enabled, copies again that day
- Re-preflight: FAIL (fixable). The check had no trigger, "once" was undefined, the doctor line had two owners, and the brief still named the issue's writer path
- Operator decision (2026-10-20): the session-start hook starts the check as a hidden internal job, so it reaches other machines with the plugin update. No nightly-job step, no hand-run command
- Re-plan done: `milestones.md` and `projectbrief.md` amended for the four findings (still 7 milestones)
- Third preflight: PASS WITH ADVISORY
- Operator decision (2026-10-21): adopt the lock time limit, the table-by-table ZSTD copy, the no-warehouse and below-head retrying skips, and the measured rehearsal (sizes, times, lowest free disk, index top-10 match share, printed by doctor). Do not hide the internal entry point from `--help`
- Fourth preflight: PASS WITH ADVISORY
- Operator decision (2026-10-21): fold advisories 1 to 4 (retry meaning, child-process builder, live-size estimate, copy order) into milestones 4 to 6, and split milestone 6 into the check and the session-start hook launch. Declined: writer step-aside
- Fifth preflight: PASS WITH ADVISORY
- Operator decision (2026-10-21): fold fifth-run advisories 1 to 4 (lock holder writes the record, detached launch, a real no-rebuild test, doctor never creates the home folder) and run preflight once more. Declined: index build after releasing the lock
- Operator decision (2026-10-21): milestones 5 to 8 are a short-lived migration utility for about five or six installs, kept a month or two, then removed. Reliable, not bulletproof; data safety unchanged. Applied: crash and overrun are final, the time limit ends the process, the rehearsal is trimmed, one fixture, and the chain stays in its own module

- Sixth preflight (lens applied): PASS WITH ADVISORY. Folded advisories 1 to 4: lock before reading or deleting, start time in the started entry, alarm only in the entry point's process, doctor's backup line outlives the chain. Not adopted: per-machine config key for the swap

## Next Step
- Plan is final. In a new window, `/niko` starts milestone 1 (new warehouses in v1.5.0+ with ZSTD)
