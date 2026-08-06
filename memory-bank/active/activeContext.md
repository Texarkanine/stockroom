# Active Context

## Current Task: fix-dashboard-sessions-ellipsis-order
**Phase:** QA - IN-PROGRESS

## What Was Done
- Confirmed defect: bottom block was the 10 oldest in ASC wire order (absolute oldest first under the ellipsis).
- Kept membership (10 oldest) but reverse to DESC for newest→older reading through the fold.
- Updated `sessions_ends` + contract test; `make test` green; draft PR #117.

## Next Step
- Level 1 semantic QA against project brief.
