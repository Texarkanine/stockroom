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
