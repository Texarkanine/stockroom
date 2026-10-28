# Active Context

## Current Task: Soak clock starts when the new warehouse is live
**Phase:** PLAN - COMPLETE

## What Was Done
- Revised the Level 2 plan after a fixable preflight. The missing soak stamp runs only when the backup and the live warehouse are both files and their inodes differ.
- Named the existing tests that keep their assertions, and the two fixtures that gain `swapped_at` so they still test what they say.
- The Rework section replaces the brief clauses that measure 14 days from `started_at`. Acceptance criteria 7 and 12 stay.

## Next Step
- Preflight the revised plan.
