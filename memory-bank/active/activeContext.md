# Active Context

## Current Task: warehouse-file-growth
**Phase:** PLAN - COMPLETE (re-plan after the seventh preflight, FAIL fixable)

## What Was Done
- Operator decision (2026-10-21): DuckDB 2.0 is the first milestone; there is no 2.0-only release. Milestones 1 to 8 ship in one release after the operator shadow-tests a branch clone on his Macs
- Operator decision (2026-10-21): every release must stand alone, because users skip releases
- Operator decision (2026-10-21): new files and the copy use storage `v2.0.0` (not `v1.5.0`)
- Operator decision (2026-10-21): this checkout (the live engine here) stays on DuckDB 1.5.4 until the shadow test passes on this machine
- Operator decision (2026-10-21): the DuckDB 2.0 sub-run may rewrite DuckDB-behaviour sentences in later milestones
- Folded the seventh preflight's three findings and its advisories into `milestones.md` and `projectbrief.md`

## Next Step
- Preflight validates the re-planned milestone list
