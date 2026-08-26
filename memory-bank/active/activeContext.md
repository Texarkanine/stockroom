# Active Context

## Current Task: dashboard-subagent-pills
**Phase:** REFLECT COMPLETE

## What Was Done
- Built all five plan units (TDD). Association, `session_detail` payload, hash/export helpers, transcript mount, and session-fragment docs are in.
- Live UAT on a **separate** worktree dashboard at `:58018` (did not touch `:58008`). Parent `604ead72-0402-49f2-bceb-c22ebed2ec33` shows one pill on turn 48 (`#msg-48-sa-1`, label `L3 QA 16-hex-leafset`) linking to child `bc960b66-605b-4e83-baac-be61435555f5`. Child view shows `parent:` back to `#msg-48-sa-1`. Untyped Task at msg 55 is not a slot — no second pill.
- QA passed with no blocking semantic findings. Lint, format, 133 JavaScript tests, and 840 Python tests passed; 4 Python tests skipped.
- Reflection written: `memory-bank/active/reflection/reflection-dashboard-subagent-pills.md`. Persistent files scanned; no surgical updates (techContext already names both fragment forms from Build unit 5).

## Operator decisions
- **Claude unmatched spawn id:** refuse to guess. No leftover placement.
- **JSON export:** keep `messages[].subagents` and `parent_spawn`. Do not redact.
- **Harness→technique map:** `claude` → provenance join, `cursor` → corroborated zip, unknown → no placements. Comment the map in `spawns.py`: a third harness is the cue to extract the techniques, not another `elif` with Cursor knobs.
- **Pills are positive claims:** omit rather than guess. Missing a pill is acceptable; a pill on the wrong turn is not.

## Cursor corroboration
- Candidates: children with non-null `agent_type`, `source_path` order. Slots: typed Tasks (`_parent_subagent_types`).
- **Aligned zip** only if counts equal and each `child.agent_type == slot.subagent_type`.
- Else **unique type** pairs only (`agent_type` appears once on both sides).
- Extra children, null `agent_type`, count holes with colliding types: omit. No last-Task / last-message leftover.
- Residual: two compensating holes when every remaining pair shares one type still looks aligned. No further warehouse signal.

## Next Step
- Run `/niko-archive` to create the archive document and finalize the current project.
