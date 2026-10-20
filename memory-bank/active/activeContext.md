# Active Context

## Current Task: torch-failures-help
**Phase:** PLAN - COMPLETE

## What Was Done
- Classified the rework as Level 2.
- Planned one `start_encoder` helper. A missing torch import with a usable freeze calls an injected healer (production: `ensure_engine_env`) once, prints that the restore is in progress, and retries once. Failure prints the reason and `sr-initialize`.
- No freeze and encoder exceptions stay interruptions and no longer claim a pip command or a wrong wheel. `doctor smoke` stays report-only.

## Next Step
- Preflight validation.
