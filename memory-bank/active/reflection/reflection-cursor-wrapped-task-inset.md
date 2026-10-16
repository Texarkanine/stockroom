---
task_id: cursor-wrapped-task-inset
date: 2026-10-15
complexity_level: 2
---

# Reflection: cursor-wrapped-task-inset

## Summary

Cursor Task launches that go out as `CallDynamicTool` now get the dashboard subagent inset, including a CLI child whose `subagentInfo` names its parent. The build matches the plan, and QA passed.

## Requirements vs Outcome

The four requirements are in the code. A wrapped `cursor` / `Task` call is a spawn slot, a CLI child is linked from `subagentInfo`, native Task zips still place, and the Claude join is unchanged. The inset on the linked live session is not updated by this build. Incremental ingest skips unchanged stores, and this worktree does not restart the dashboard on port 58008. That boundary was in the plan.

## Plan Accuracy

The three-step order held, and the files were the right ones. `model.py` needed a docstring fix the plan did not name: `spawning_tool_use_id` was described as Claude-only. `_corroborated_zip` became unused once cursor placement moved to `_cursor_placements`, so it was removed. The newline inside `toolCallId` showed up exactly as the plan expected, and the parser test keeps it. The preflight and QA both advised one shared unwrap helper. The plan's sibling pair stayed.

## Build & QA Observations

The new tests failed before the production change and passed after it. Existing zip and Claude join tests stayed green. QA passed on the first review and added no fix. `make test` reported 900 passed and one failure, `test_docs_lock_is_not_stale`, because this machine's uv is 0.8.22 and the root lock is revision 5. CI uses uv 0.12.22. The lock file was not changed.

## Insights

### Technical

- A CLI `toolCallId` can contain a newline. The join works only when `spawning_tool_use_id` and `source_tool_use_id` keep that byte string.
- `0001_initial_schema.sql` still says Cursor `spawning_tool_use_id` is NULL. CLI children now set it. Applied migrations stay as written.

### Process

Nothing notable

### Million-Dollar Question

The association we built is the one to keep: join on a recorded tool id, and zip only the launches that have no id. The smaller elegance is one `cursor_task_input` helper shared by ingest and the dashboard, which is what both reviews advised and what the existing sibling split left as two copies.
