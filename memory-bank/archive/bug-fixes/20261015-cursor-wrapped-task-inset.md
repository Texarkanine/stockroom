---
task_id: cursor-wrapped-task-inset
complexity_level: 2
date: 2026-10-15
status: completed
---

# TASK ARCHIVE: cursor-wrapped-task-inset

## SUMMARY

A Cursor parent that launches a subagent by calling Task through `CallDynamicTool` (namespace `cursor`, tool name `Task`) now gets the normal dashboard subagent inset. CLI children take their parent link from store `meta.subagentInfo`. Native Task insets and Claude spawn-id insets stay as they were. The operator pointed this worktree's shim and dashboard at the live warehouse, ran a full Cursor ingest, and confirmed the inset. Pull request [#140](https://github.com/Texarkanine/stockroom/pull/140) is open.

## REQUIREMENTS

1. A Cursor parent turn that launches a subagent through `CallDynamicTool` shows the existing subagent pill (`#msg-N-sa-M`).
2. A CLI child whose `subagentInfo` names the parent (`parentAgentId`, `toolCallId`, `typeName`) is the child that pill opens.
3. Native Cursor Task launches keep their current insets.
4. Claude spawn-id insets stay as they are.

The motivating pair is message 42 of Cursor session `5fa10c9d-2c18-42d6-b491-41503d6dc01b` and child `43b093cd-f419-4bee-b60b-56d1f5075d0c`.

## IMPLEMENTATION

No schema change. Child identity is a warehouse fact written at ingest. Which parent turn gets the pill stays a dashboard read.

`cursor_chats.parse_session` stamps a CLI child when `meta.subagentInfo` is a dict and `parentAgentId` is a non-empty string: `is_subagent`, `parent_session_id` from `parentAgentId`, `agent_type` from a non-empty `typeName`, and `spawning_tool_use_id` from `toolCallId` copied unchanged, including a newline. `rootParentAgentId` is ignored. Any other `subagentInfo` leaves an ordinary CLI chat.

`spawns._task_slots` treats a native `Task` with a non-null `subagent_type` as a slot, and also a `CallDynamicTool` whose namespace is `cursor`, tool name is `Task`, and nested `subagent_type` is not null. The slot's input is the nested `arguments` mapping, so the label chain reads `description`. The stored tool row stays `CallDynamicTool`. Cursor placement joins children that carry `spawning_tool_use_id` to those slots, then runs the existing aligned-or-unique zip on whoever is left. A child whose id matches no slot stays omitted. Claude still joins on `source_tool_use_id`.

`cursor._parent_subagent_types` uses the same wrapped-call rule, in transcript order, so an IDE child's positional `agent_type` includes a wrapped Task. IDE `spawning_tool_use_id` stays null.

`NormalizedSession.spawning_tool_use_id` is no longer documented as Claude-only. Preflight and QA both advised one shared unwrap helper. The sibling pair stayed, each side tested and cross-referenced.

Key files: `skills/sr-search/src/stockroom/ingest/cursor_chats.py`, `skills/sr-search/src/stockroom/ingest/cursor.py`, `skills/sr-search/src/stockroom/ingest/model.py`, `skills/sr-search/src/stockroom/dashboard/spawns.py`, and the matching tests in `test_ingest_cursor_chats.py`, `test_ingest_cursor.py`, `test_dashboard_spawns.py`, and `test_dashboard_metrics.py`.

## TESTING

- New tests failed before the production change and passed after it. Existing Cursor zip and Claude join tests stayed green.
- QA targeted the four affected files: 101 passed. `ruff check` and `ruff format --check` were clean. Verdict PASS.
- `make test`: 134 JavaScript tests passed; pytest 900 passed, 4 skipped, 1 failed. The failure is `test_docs_lock_is_not_stale` because this machine's uv is 0.8.22 and the committed root lock is revision 5. CI checks that lock with uv 0.12.22. The lock file was not changed.
- Preflight PASS WITH ADVISORY. The advisory was the shared unwrap helper, left as a sibling pair.
- After the build, the operator switched the on-path shim and the dashboard on port 58008 to this worktree, ran a full ingest, and confirmed the live session looks right. Incremental ingest would have skipped the unchanged stores.

## LESSONS LEARNED

- A CLI `toolCallId` can contain a newline. The join works only when `spawning_tool_use_id` and the parent `source_tool_use_id` keep that byte string.
- `0001_initial_schema.sql` still says Cursor `spawning_tool_use_id` is NULL. CLI children now set it. Applied migrations are not rewritten.
- "Being a subagent" is stored on the session row. Pill placement is inferred at read time from those rows. CLI parentage lives only in `store.db` until ingest copies it, so already-ingested stores stay unlinked until `stockroom ingest --full`.

## PROCESS IMPROVEMENTS

Nothing notable. The three-step plan held, and QA passed on the first review.

## TECHNICAL IMPROVEMENTS

One `cursor_task_input` helper shared by ingest and the dashboard would remove the duplicated unwrap predicate. Both reviews advised it. The shipped sibling split leaves that as a later cleanup, not a behavior change.

## NEXT STEPS

Pull request [#140](https://github.com/Texarkanine/stockroom/pull/140) is open.
