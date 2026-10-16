# Task: cursor-wrapped-task-inset

* Task ID: cursor-wrapped-task-inset
* Complexity: Level 2
* Type: bug fix

A Cursor parent that launches a subagent by calling Task through `CallDynamicTool` (namespace `cursor`, tool name `Task`) does not get a dashboard subagent inset. CLI children record the link in store `meta.subagentInfo` (`parentAgentId`, `toolCallId`, `typeName`), and ingest ignores that record, so the child is stored as an ordinary session. The inset only treats a tool whose name is `Task` as a spawn slot. Native Task insets and Claude spawn-id insets stay as they are.

No documentation update. The user guide describes the pill hash, not which tool shape produces a pill. The IDE fixture note still describes a structural link with no child id.


## Test Plan (TDD)

### Behaviors to Verify

- CLI `subagentInfo`: a `store.db` whose meta `subagentInfo` has a non-empty `parentAgentId`, `typeName`, and `toolCallId` → `parse_session` sets `is_subagent`, `parent_session_id`, `agent_type`, and `spawning_tool_use_id` to those values, and a newline inside `toolCallId` is kept
- CLI non-child: no `subagentInfo`, a non-dict `subagentInfo`, or an empty `parentAgentId` → `is_subagent` is false and `parent_session_id`, `agent_type`, and `spawning_tool_use_id` stay unset
- Wrapped slot: `associate_children("cursor", …)` with a `CallDynamicTool` whose input is namespace `cursor`, tool name `Task`, and nested `subagent_type` plus `description` → one placement on that message, label equal to the nested description
- Id join beats zip: two `generalPurpose` children, one whose `spawning_tool_use_id` equals the wrapped tool's `source_tool_use_id` and whose `source_path` would sort after the other → only the id-matching child is placed, on that tool's message
- Not a slot: a `CallDynamicTool` whose tool name is not `Task`, whose namespace is not `cursor`, or whose nested `subagent_type` is null → no placement
- Missed id stays omitted: a child with a `spawning_tool_use_id` that matches no slot is not placed, including when its `agent_type` is unique
- IDE order: a parent whose tool calls are a wrapped Task (`explore`) and then a native Task (`generalPurpose`) → `parse_subagent` index 0 gets `explore`, index 1 gets `generalPurpose`, and `spawning_tool_use_id` stays null
- Session payload: `session_detail` for a cursor parent whose stored tool is that wrapped Task, and a child row with `parent_session_id`, `agent_type`, and the matching `spawning_tool_use_id` → that message's `subagents` entry uses the nested description as `label`, and the child detail's `parent_spawn` points at that message ordinal
- Existing cursor zip and Claude join: parents whose tools are native `Task` calls, and Claude joins on `source_tool_use_id`, keep the placements the current tests assert

### Test Infrastructure

- Framework: pytest, as configured in `skills/sr-search/pyproject.toml`
- Test location: `skills/sr-search/tests/`
- Conventions: one behavior per test function, docstring states the contract, CLI stores are built with the existing `_write_store` helper, dashboard metrics use `_seed_session` and `_seed_tool`
- New test files: none

## Implementation Plan

### 1. CLI subagent linkage — executable

- [x] Step complete

- Files: `skills/sr-search/src/stockroom/ingest/cursor_chats.py`, `skills/sr-search/tests/test_ingest_cursor_chats.py`

1. Stub tests: in `test_ingest_cursor_chats.py`, add empty tests for a `subagentInfo` child (including a newline in `toolCallId`) and for the three non-child shapes.
2. Stub interface: no new function. `parse_session` already returns `NormalizedSession`. Extend its docstring to name `subagentInfo`.
3. Write tests and run red: build stores with `_write_store`. Assert the child fields and that a newline in `toolCallId` is unchanged. Assert the non-child shapes leave `is_subagent` false and the three link fields unset. The existing fixture test that expects `is_subagent` false stays as it is.
4. Write code and run green: in `parse_session`, when `meta["subagentInfo"]` is a dict and `parentAgentId` is a non-empty string, set `is_subagent`, `parent_session_id` from `parentAgentId`, `agent_type` from a non-empty string `typeName`, and `spawning_tool_use_id` from a non-empty string `toolCallId` with no stripping. Ignore `rootParentAgentId`. Any other `subagentInfo` leaves the session an ordinary CLI chat.

### 2. Wrapped Task slots and id join — executable

- [x] Step complete

- Files: `skills/sr-search/src/stockroom/dashboard/spawns.py`, `skills/sr-search/tests/test_dashboard_spawns.py`, `skills/sr-search/tests/test_dashboard_metrics.py`

1. Stub tests: in `test_dashboard_spawns.py`, add empty tests for the wrapped slot, the id-join-over-zip case, the three non-slots, and the missed id. In `test_dashboard_metrics.py`, add an empty `session_detail` test for the wrapped tool plus matching child.
2. Stub interface: no new public function. `_task_slots` keeps its signature and gains the wrapped-tool case. Add a private cursor combiner that calls the existing join and zip helpers, and point the `"cursor"` technique at it. Update the `associate_children` docstring.
3. Write tests and run red: a wrapped tool's placement label is the nested `description`. Two same-type children place only the one whose `spawning_tool_use_id` equals that tool's `source_tool_use_id`. A non-Task name, a non-`cursor` namespace, and a null nested `subagent_type` place nothing. A child whose id matches no slot is omitted even when its type is unique. `session_detail` nests that child on the parent message and sets the child's `parent_spawn` to that ordinal. Run the new tests and confirm they fail.
4. Write code and run green: `_task_slots` keeps a native `Task` whose `subagent_type` is not null. It also accepts `CallDynamicTool` when `namespace` is `cursor`, `toolName` is `Task`, `arguments` is a mapping, and `arguments.subagent_type` is not null. The slot keeps `message_ordinal`, `tool_ordinal`, and `source_tool_use_id`, and its `tool_input` is that `arguments` mapping so the existing label chain reads `description`. The stored tool row is not rewritten. The cursor combiner joins children that have a `spawning_tool_use_id` to those slots only, drops joined children and their slots from the zip, runs the existing aligned-or-unique zip on what remains, and assigns `spawn_index` once over the combined pairs ordered by `source_path` then `session_id`. Children with a spawn id that misses a slot stay out of the zip. Claude still uses `_provenance_join` on every tool. Run the new tests and the existing spawn and session-detail tests.

### 3. IDE positional types include wrapped Task — executable

- [x] Step complete

- Files: `skills/sr-search/src/stockroom/ingest/cursor.py`, `skills/sr-search/tests/test_ingest_cursor.py`

1. Stub tests: in `test_ingest_cursor.py`, add an empty test that a wrapped Task followed by a native Task assigns `agent_type` by index and leaves `spawning_tool_use_id` null.
2. Stub interface: no new function. `_parent_subagent_types` keeps its signature. Extend its docstring to include the wrapped call.
3. Write tests and run red: build a parent `NormalizedSession` whose tool calls are the wrapped `explore` call and then a native `generalPurpose` Task, write two minimal subagent jsonl files, and assert `parse_subagent` index 0 and 1. Confirm the test fails on index 0.
4. Write code and run green: `_parent_subagent_types` walks tool calls in message order and appends `subagent_type` for a native `Task` or for a `CallDynamicTool` that meets the same three conditions as `_task_slots` (`namespace` `cursor`, `toolName` `Task`, nested `subagent_type` not null). A comment in each function names the other as the sibling rule. `parse_subagent` still sets `spawning_tool_use_id` to null.

## Technology Validation

No new technology - validation not required

## Dependencies

- pytest and the existing dashboard DuckDB fixture helpers
- No new packages
- The operator warehouse and the dashboard on port 58008 are not build inputs

## Challenges & Mitigations

- `toolCallId` on the example child contains a newline joining two ids. The parent tool row already stores that same string as `source_tool_use_id`. Copy `toolCallId` unchanged into `spawning_tool_use_id`, and cover the newline in the parser test.
- Incremental ingest skips a store whose `(mtime, path)` is not newer than the watermark. Rows already in the warehouse stay unlinked until `stockroom ingest --full` (or those stores are newer). This build does not run ingest against the operator warehouse, and it does not restart the dashboard on port 58008.
- A cursor child with a spawn id must not fall through into the source-path zip, and an IDE slot must not be dropped just because its tool-use id is set. The combiner joins only children that have a spawn id, and it removes a slot only when a child joined to that id.
- `_task_slots` and `_parent_subagent_types` are the existing sibling pair and will both learn the wrapped shape. Each side has its own test so a drift in namespace, tool name, or nested `subagent_type` fails one of them.
- A CLI child stamped `is_subagent` drops out of dashboard metrics and the top-level sessions list, which is the existing subagent contract. The pill and a direct session URL still open it.

## Pre-Mortem

- Placing CLI children with the source-path zip would pair two `generalPurpose` children in UUID order. The plan joins on `toolCallId` first and keeps those children out of the zip.
- Rewriting the stored tool name from `CallDynamicTool` to `Task` would hide the call the transcript recorded. The plan unwraps only inside the slot view.
- Treating the inset as a read-time decoration of the tool call, without a child row, would leave the example session without a pill: placement loads children by `parent_session_id`. The plan stamps that link from `subagentInfo` at ingest.
- Calling this a new association architecture would re-level it. The plan uses the two techniques `spawns.py` already has, on the slots the IDE type list already mirrors.

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Pre-Mortem complete
- [x] Preflight
- [x] Build
- [ ] QA
