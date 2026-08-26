# Active Context

## Current Task: dashboard-subagent-pills
**Phase:** PREFLIGHT - COMPLETE (PASS WITH ADVISORY)

## What Was Done
- Re-planned after the first preflight `FAIL (blocking)`. Second preflight: `PASS WITH ADVISORY`.
- Operator forks are plan invariants: Claude unmatched spawn ids are omitted; JSON export keeps `messages[].subagents` and `parent_spawn`.
- Association helper takes parent `message_ordinals`. Queries use `(harness, session_id)`. Render is a testable model before `dashboard.mjs` / `index.html` edits. Hashchange uses a generic fragment helper.

## Operator decisions
- **Claude unmatched spawn id:** refuse to guess. No leftover placement.
- **JSON export:** keep `messages[].subagents` and `parent_spawn`. Do not redact.

## Build notes from preflight
- Name `_parent_subagent_types` in the `spawns.py` docstring (typed-Task slot rule lives in two places).
- Unrecognized harness: produce no placements (do not inherit the Cursor zip).
- Pill and `parent:` links are plain `<a href>` (full reload). Deliberate; boot already honors `?view=session…#msg-N-sa-M`.
- Do not extend `sessionLocationWithMessageHash` with `spawnIndex` unless a consumer appears.
- Give unmatched-Claude-viewed-directly its own named `session_detail` test; do not rely on `test_session_detail_serves_subagent_when_addressed_directly`.
- Advisory `placements(con, harness, session_id)` declined for this task (same YAGNI as `association_method`).

## Next Step
- Operator: invoke `/niko-build`.