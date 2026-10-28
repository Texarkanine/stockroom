# Active Context

## Current Task: Soak clock starts when the new warehouse is live
**Phase:** PREFLIGHT - COMPLETE (PASS WITH ADVISORY)

## What Was Done
- Revised the plan again. `test_replace_that_lands_resumes_without_copying` resumes at a later clock and expects `swapped_at` from that clock.
- `OSError` on the new file check starts the child and does not crash the stamp. The rehearsed record, not the hand-written round trip, shows `swapped_at is None`.
- Use-cases 1, 3, and 4 are in the list of brief clauses this rework replaces.

## Next Step
- Build unit 1. The preflight passed with advisory.
