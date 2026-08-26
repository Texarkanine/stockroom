# Active Context

## Current Task: dashboard-subagent-pills
**Phase:** PLAN - COMPLETE (re-plan after blocking preflight)

## What Was Done
- Re-planned after preflight `FAIL (blocking)`. Operator forks are now plan invariants: Claude unmatched spawn ids are omitted; JSON export keeps `messages[].subagents` and `parent_spawn`.
- Association helper now takes parent `message_ordinals` so Cursor leftover works with no tools. Child/parent/sibling queries require `(harness, session_id)`.
- Session render is specified by a testable `sessionTranscriptItems` / `sessionParentLine` model before `dashboard.mjs` / `index.html` change. Hashchange will use a generic fragment helper that accepts `#msg-N` and `#msg-N-sa-M`.
- Preflight advisory `association_method` is out of scope.

## Operator decisions
- **Claude unmatched spawn id:** refuse to guess. If `spawning_tool_use_id` does not join a parent tool, do not invent a turn. No leftover placement for that child.
- **JSON export:** keep `messages[].subagents` and `parent_spawn`. Do not redact.

## Next Step
- Spawn `/niko-preflight` to validate the repaired plan.