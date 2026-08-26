# Active Context

## Current Task: dashboard-subagent-pills
**Phase:** QA - COMPLETE (PASS)

## What Was Done
- Built all five plan units (TDD). Association, `session_detail` payload, hash/export helpers, transcript mount, and session-fragment docs are in.
- Live UAT on a **separate** worktree dashboard at `:58018` (did not touch `:58008`). Parent `604ead72-0402-49f2-bceb-c22ebed2ec33` shows one pill on turn 48 (`#msg-48-sa-1`, label `L3 QA 16-hex-leafset`) linking to child `bc960b66-605b-4e83-baac-be61435555f5`. Child view shows `parent:` back to `#msg-48-sa-1`. Untyped Task at msg 55 is not a slot — no second pill.
- QA passed with no blocking semantic findings. Lint, format, 133 JavaScript tests, and 840 Python tests passed; 4 Python tests skipped.

## Operator decisions
- **Claude unmatched spawn id:** refuse to guess. No leftover placement.
- **JSON export:** keep `messages[].subagents` and `parent_spawn`. Do not redact.
- **Harness→technique map:** `claude` → provenance join, `cursor` → corroborated zip, unknown → no placements. Comment the map in `spawns.py`: a third harness is the cue to extract the techniques, not another `elif` with Cursor knobs.
- **Pills are positive claims:** omit rather than guess. Missing a pill is acceptable; a pill on the wrong turn is not.

## Cursor corroboration
- Candidates: children with non-null `agent_type`, `source_path` order. Slots: typed Tasks (`_parent_subagent_types`).
- **Aligned zip** only if counts equal and each `child.agent_type == slot.subagent_type`.
- Else **unique type** pairs only (`agent_type` appears once on both sides).
- Extra children, null `agent_type`, count holes with colliding types: omit. No last-Task / last-message leftover. `message_ordinals` dropped from the helper.
- Residual: two compensating holes when every remaining pair shares one type still looks aligned. No further warehouse signal.

## Files created or modified
- Created: `skills/sr-search/src/stockroom/dashboard/spawns.py`, `skills/sr-search/tests/test_dashboard_spawns.py`
- Modified: `metrics.py`, `test_dashboard_metrics.py`, `dashboard-session.mjs`, `dashboard-session.test.mjs`, `dashboard.mjs`, `index.html`, `docs/user-guide/dashboard.md`, `memory-bank/techContext.md`

## Build decisions (not already in creative docs)
- `h3.session-subagent-heading` at `0.95rem` so the heading-as-link matches session chrome without inventing a new type scale.
- Pill / `parent:` links stay plain `<a href>` (full reload). Existing SPA click interceptors were not attached. Hash boot already honors `#msg-N-sa-M`.
- Did not extend `sessionLocationWithMessageHash` with `spawnIndex` (no extra consumer).
- Live verification used port **58018** so the machine's one live dashboard on `:58008` stayed untouched.

## Deviations from plan
None material — built to plan. Residual Cursor risk (two compensating holes, one shared type) remains documented, not "fixed."

## Integration / UAT
- Seeded integration: `session_detail` nests `subagents` / `parent_spawn` in agreement with `associate_children`; same `session_id` on two harnesses does not leak.
- `make test-dashboard-js`: 133 passed. `make test-dashboard-py`: 170 passed. `make lint` + `make format-check`: clean. `make test`: 133 JS + 840 pytest passed, 4 skipped.
- Live parent: 79 turns, 1 pill, `#msg-48` still present, `parent:` hidden. Live child: 19 turns, `parent:` visible, no grandchild pills. Browser-tool click on `parent:` focused the link but did not navigate; hop-back verified via href + hash boot (pill in view at `#msg-48-sa-1`).

## Next Step
- Proceed to `/niko-reflect`.
