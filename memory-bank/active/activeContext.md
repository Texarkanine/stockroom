# Active Context

## Current Task: warehouse-file-growth
**Phase:** PLAN - COMPLETE (amended 2026-10-21: DuckDB 2.0 first milestone, skip-safe releases)

## What Was Done
- `/niko` classified the format milestone as a Level 2 sub-run, then the plan phase found a decision for the operator: move to DuckDB 2.0 (LTS, released 2026-10-21) before the format work
- Operator decision (2026-10-21): DuckDB 2.0 becomes the new first milestone, released on its own before the copy chain. The sub-run classification was withdrawn and the Level 4 state restored
- Operator decision (2026-10-21): every release must stand alone, because users skip releases. No milestone may assume a user ran an earlier release of this project, the check, or the swap
- Milestone list amended to 9 milestones. Brief amended (requirements 9 and 10, acceptance 10 and 11)

## Next Step
- Preflight validates the amended milestone list
