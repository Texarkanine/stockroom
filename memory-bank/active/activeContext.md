# Active Context

## Current Task: fix-dashboard-sessions-ellipsis-order
**Phase:** BUILD - IN-PROGRESS

## What Was Done
- Classified as Level 1 (quick bug fix): investigate/fix Sessions panel ordering below the ellipsis fold; single dashboard surface, low risk.
- Prior art: archive `20260714-dashboard-sessions-browse` documents intentional `10 newest + … + 10 oldest` with oldest ASC — investigation must distinguish design vs defect.

## Next Step
- Locate root cause: confirm whether bottom-block ASC order is wrong for reading continuity; write failing test and fix only if needed.
