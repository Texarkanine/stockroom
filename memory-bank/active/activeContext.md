# Active Context

## Current Task: dashboard-subagent-pills
**Phase:** BUILD - IN-PROGRESS

## What Was Done
- Re-planned after the first preflight `FAIL (blocking)`. Second preflight: `PASS WITH ADVISORY`.
- Operator then forbade false-positive pills: Cursor leftover is gone; zip runs only when corroborated.

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

## Build notes from preflight
- Name `_parent_subagent_types` in the `spawns.py` docstring. The harness→technique map comment is the other breadcrumb.
- Pill and `parent:` links are plain `<a href>` (full reload). Deliberate; boot already honors `?view=session…#msg-N-sa-M`.
- Do not extend `sessionLocationWithMessageHash` with `spawnIndex` unless a consumer appears.
- Give unmatched-Claude-viewed-directly its own named `session_detail` test; do not rely on `test_session_detail_serves_subagent_when_addressed_directly`.
- Advisory `placements(con, harness, session_id)` declined for this task (same YAGNI as `association_method`).

## Next Step
- Unit 2: `session_detail` payload (`subagents` / `parent_spawn`) — TDD.