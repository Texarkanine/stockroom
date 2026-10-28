# Active Context

## Current Task: Soak clock starts when the new warehouse is live
**Phase:** PLAN - COMPLETE

## What Was Done
- Level 2 plan: unlink from `swapped_at`, stamp that field when the record becomes `swapped`, and stamp an already-swapped record that lacks it so the parent still launches once.
- `started_at` stays the four-hour alarm. There is no fallback from a missing `swapped_at` to `started_at`.

## Next Step
- Preflight the plan.
