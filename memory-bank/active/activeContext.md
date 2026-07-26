# Active Context

## Current Task: fix-dashboard-token-tooltip-overflow
**Phase:** BUILD - COMPLETE

## What Was Done
- Root cause: absolute+centered token popover trapped in `.table-scroll` overflow
- Added `tokenBreakdownPlacement` (below-prefer / flip / clamp) and fixed-position CSS
- Wired mount to sync on pointerenter/focusin
- Tests: JS placement cases + static CSS contract; full suite green

## Next Step
- Enter QA phase (`/niko-qa` Level 1)
