# Active Context

## Current Task: cursor-wrapped-task-inset
**Phase:** PLAN - COMPLETE

## What Was Done
- Planned a Level 2 bug fix in three test-first steps.
- CLI `parse_session` will stamp `is_subagent`, `parent_session_id`, `agent_type`, and `spawning_tool_use_id` from `meta.subagentInfo` when `parentAgentId` is a non-empty string. `toolCallId` is copied unchanged.
- Dashboard cursor placement will treat `CallDynamicTool` (namespace `cursor`, tool name `Task`, nested `subagent_type`) as a Task slot, join children that carry `spawning_tool_use_id` to those slots, and run the existing zip only on the children and slots left over.
- IDE `_parent_subagent_types` will collect that same wrapped shape in transcript order so positional `agent_type` stays aligned with the slots. IDE `spawning_tool_use_id` stays null.
- The stored tool row stays `CallDynamicTool`. This build does not re-ingest the operator warehouse and does not restart the dashboard on port 58008.

## Next Step
- Preflight validation, in a subagent, via `/niko-preflight`.
