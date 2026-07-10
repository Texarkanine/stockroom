# Active Context

## Current Task: dashboard-polish-m2-write-read-ratio
**Phase:** PLAN - COMPLETE

## What Was Done
- Planned m2 (#6): rewrite `buildWriteReadPanel` to ratio series (aggregate one line / compare per harness) with `null` on 0/0
- TDD mapped to `dashboard-core.test.mjs` + static aria contract; adapter gets colors + 0–1 Y scale; no Python change

## Decisions
- Ratio definition: `writes / (writes + reads)`; Y-axis 0–1 via model `yMax`
- Idle weeks → `null` gaps; write=0 with reads>0 → finite `0` (panel not empty)
- Empty detection scoped so count panels keep “all zeros → empty”

## Next Step
- Preflight validation runs automatically
