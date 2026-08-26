# Active Context

## Current Task: dashboard-subagent-pills
**Phase:** PREFLIGHT - COMPLETE (FAIL (blocking))

## What Was Done
- Classified Level 3. Resolved two creatives: spawn-to-turn association (Claude join + Cursor typed-Task zip) and pill chrome (sibling inset + `parent:` under session metadata).
- Planned five implementation units: `spawns.py` helper, `session_detail` payload, JS hash/parent helpers, session render/CSS, docs.
- Operator settled the two preflight product forks.

## Operator decisions
- **Claude unmatched spawn id:** refuse to guess. If `spawning_tool_use_id` does not join a parent tool, do not invent a turn. No leftover placement for that child. Claude Code is assumed to provide good data; bad rows are not rendered as if they were good.
- **JSON export:** keep `messages[].subagents` and `parent_spawn`. Do not redact. Export is enough to rebuild a UI in front of the JSON; that is the vibe, not a hard product promise.

## Next Step
- Resume with `/niko-plan` (not `/niko-build`). Repair the blocking preflight findings using the operator decisions above, then re-run preflight.
