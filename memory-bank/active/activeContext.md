# Active Context

## Current Task: p3-m2-stockroom-shim
**Phase:** PREFLIGHT (RE-RUN) - COMPLETE (PASS)

## What Was Done
- **Operator decisions (2026-07-08, at the preflight→build gate):**
  - HARD NO on any runtime self-resolution in the shim — succeed correctly or refuse; never guess
  - Session-start hook rectifies the shim (feasibility confirmed: both harnesses export the plugin root to hook processes)
  - Two-harness case: explicit ownership; init declines to manage a live foreign shim; takeover only against a dead incumbent
- Q1 creative doc rewritten (baked-only shim + hook rectification + ownership supersedes always-scan); Q2 notes revised (pinned mode collapsed; `install`/`rectify` subactions)
- Plan rebuilt in `tasks.md`: 8 implementation steps; new artifacts `hooks/cursor-hooks.json` + `hooks/claude-hooks.json` + manifest pointers; packaging-contract tests pin the hook wiring; live hook firing is operator-artisanal (flagged for QA)

## Next Step
- Operator runs `/niko-build` to begin implementation
