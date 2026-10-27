# Active Context

## Current Task: Fortnight backup reclaim and finished-home short-circuit
**Phase:** COMPLEXITY-ANALYSIS - COMPLETE

## What Was Done
- Classified as Level 3. Issue 154 and item 1 of issue 155 are one check feature: unlink `warehouse.issue147-swap.duckdb` on the `swapped` stop path a fortnight after `started_at`, and return before `launch()` when version 1 is `swapped`, `already-new`, or `mismatch` and that backup is not a file.
- Not Level 2: the short-circuit must still spawn when the backup is present, or the unlink never runs. A wrong predicate can remove the live warehouse or skip an in-progress home. The change crosses the check pass, the import boundary of the hooked module, and the restore docs.
- Not Level 4: the issues already fix the design. Item 2 of issue 155 (remove the machinery in the next major) stays out. No second record file.

## Next Step
- Load the Level 3 plan phase.
