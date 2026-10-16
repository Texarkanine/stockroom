# Active Context

## Current Task: cursor-wrapped-task-inset
**Phase:** QA - COMPLETE (PASS)

## What Was Done
- CLI `parse_session` stamps `is_subagent`, `parent_session_id`, `agent_type`, and `spawning_tool_use_id` from `meta.subagentInfo` when `parentAgentId` is a non-empty string. `toolCallId` is copied unchanged, including a newline.
- Dashboard cursor placement treats `CallDynamicTool` (namespace `cursor`, tool name `Task`, nested `subagent_type`) as a Task slot. Children with `spawning_tool_use_id` join those slots. The existing zip runs only on the children and slots left over. A missed id stays omitted.
- IDE `_parent_subagent_types` collects that same wrapped shape in transcript order. IDE `spawning_tool_use_id` stays null.
- The stored tool row stays `CallDynamicTool`.

## Files modified
- `/home/mobaxterm/worktrees/Texarkanine/stockroom/stockroom-cursor-subagents/skills/sr-search/src/stockroom/ingest/cursor_chats.py`
- `/home/mobaxterm/worktrees/Texarkanine/stockroom/stockroom-cursor-subagents/skills/sr-search/src/stockroom/ingest/cursor.py`
- `/home/mobaxterm/worktrees/Texarkanine/stockroom/stockroom-cursor-subagents/skills/sr-search/src/stockroom/ingest/model.py`
- `/home/mobaxterm/worktrees/Texarkanine/stockroom/stockroom-cursor-subagents/skills/sr-search/src/stockroom/dashboard/spawns.py`
- `/home/mobaxterm/worktrees/Texarkanine/stockroom/stockroom-cursor-subagents/skills/sr-search/tests/test_ingest_cursor_chats.py`
- `/home/mobaxterm/worktrees/Texarkanine/stockroom/stockroom-cursor-subagents/skills/sr-search/tests/test_ingest_cursor.py`
- `/home/mobaxterm/worktrees/Texarkanine/stockroom/stockroom-cursor-subagents/skills/sr-search/tests/test_dashboard_spawns.py`
- `/home/mobaxterm/worktrees/Texarkanine/stockroom/stockroom-cursor-subagents/skills/sr-search/tests/test_dashboard_metrics.py`

## Decisions
- Left the preflight advisory (one shared unwrap helper) as advice. The sibling rule stays in `cursor._parent_subagent_types` and `spawns._task_arguments`, and each side has a test.
- Updated the `NormalizedSession` docstring so `spawning_tool_use_id` is no longer described as Claude-only.
- Removed `_corroborated_zip` after cursor placement moved to `_cursor_placements`. The zip rule is `_zip_pairs`.

## Next Step
- QA review, in a subagent, via `/niko-qa`.
