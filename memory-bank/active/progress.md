# Progress

Show the normal dashboard subagent inset when a Cursor parent launches a subagent by calling Task through `CallDynamicTool`, including the CLI session whose stored child already names its parent in `subagentInfo`. Keep native Task insets and Claude spawn-id insets as they are.

**Complexity:** Level 2

## 2026-10-15 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - Restated the request and got operator approval
    - Classified the task as Level 2
    - Wrote the project brief, active context, and task stub
* Decisions made
    - Level 2: the inset is missing for a real spawn, and the fix crosses CLI ingest and dashboard spawn placement
* Insights
    - The example parent tool is `CallDynamicTool` with inner tool `Task`. The child store records `subagentInfo` (`parentAgentId`, `toolCallId`, `typeName`). CLI ingest does not read that record, and the inset only treats a tool named `Task` as a spawn slot
    - The same wrapper exists on IDE transcripts (22 `CallDynamicTool` calls whose inner tool is `Task`) beside native `Task` calls

## 2026-10-15 - PLAN - COMPLETE

* Work completed
    - Wrote the Level 2 plan for `cursor-wrapped-task-inset` in `memory-bank/active/tasks.md`
    - Mapped tests onto `test_ingest_cursor_chats.py`, `test_dashboard_spawns.py`, `test_dashboard_metrics.py`, and `test_ingest_cursor.py`
* Decisions made
    - Stamp CLI child identity from `meta.subagentInfo` at ingest, copying `toolCallId` unchanged
    - Unwrap `CallDynamicTool` into a Task slot only inside dashboard placement, and join id-bearing children before the existing zip
    - Teach IDE `_parent_subagent_types` the same wrapped shape, in transcript order, and leave IDE `spawning_tool_use_id` null
    - Leave the operator warehouse and the dashboard on port 58008 out of the build
* Insights
    - Every wrapped Task already stored is namespace `cursor` with nested `subagent_type` `generalPurpose` (22 IDE, 3 CLI)
    - A source-path zip of two CLI children of the same type would follow UUID order, so an id match has to win and the unmatched child has to stay omitted
