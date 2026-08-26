# Progress

Surface warehouse-linked subagent sessions in the dashboard conversation reconstruction: distinct inline pills that deep-link to the child, plus a `parent:` line on subagent views that deep-links back to the child's pill. Existing `#msg-N` numbering stays put; new anchors are `#msg-{ordinal}-sa-{n}`.

**Complexity:** Level 3

## 2026-08-26 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - Validated intent against the live example session `604ead72-0402-49f2-bceb-c22ebed2ec33` (child `bc960b66-605b-4e83-baac-be61435555f5` already in the warehouse).
    - Wrote project brief, active context, and task stub.
* Decisions made
    - Level 3: not a bug fix; spans session API, reconstruction UI, and fragment-hash contract; pill content and Cursor spawn-to-turn mapping need a design shop.
    - Parent chrome starts as `parent:` under the session metadata line unless plan/creative finds a clearly better home.
* Insights
    - Session detail already returns `is_subagent` and `parent_session_id` and will serve a subagent when addressed directly; the sessions list excludes children. The gap is transcript surfacing and parent chrome, not missing ingest rows.
    - Cursor children have `spawning_tool_use_id` NULL and are associated positionally with parent `Task` calls; Claude children carry a tool-use id. Spawn-to-turn association is the main design risk.

## 2026-08-26 - CREATIVE - COMPLETE (spawn-to-turn association)

* Work completed
    - Explored four association options against the live parent (two Task calls, one child).
* Decisions made
    - Claude: join `spawning_tool_use_id` to parent `source_tool_use_id`.
    - Cursor: zip `source_path`-sorted children to `Task` calls that have `subagent_type` (same slots as ingest `agent_type`).
    - Unmatched children hang off the last Task-bearing turn, else the last message, so `#msg-{ordinal}-sa-{n}` stays one scheme.
    - Compute in `session_detail`; nest `messages[].subagents` and child `parent_spawn`. No ingest rewrite.
* Insights
    - Parent and child `source_mtime` can be identical; time-proximity matching is not available.
    - An untyped Task ("Nudge L3 QA" at msg 55) must not consume a zip slot.

## 2026-08-26 - CREATIVE - COMPLETE (subagent pill chrome)

* Work completed
    - Compared in-turn chip, sibling inset card, and transcript-top child list against the shipped session design tokens.
* Decisions made
    - Sibling inset card after the launching turn; one heading-as-link; extra left padding and a `color-mix` tint.
    - `parent:` stays under the session metadata line; link text is parent `session_id`.
    - Server sends `label` (Task description → agent_name → title → agent_type → "Subagent").
    - No export or sessions-list changes.
* Insights
    - The spawn cannot live inside `#msg-N` if `#msg-N-sa-M` must scroll to the pill itself.

## 2026-08-26 - PLAN - COMPLETE

* Work completed
    - Component analysis, TDD map, five-step implementation plan, challenges, pre-mortem.
* Decisions made
    - New `stockroom.dashboard.spawns` helper; `session_detail` is the only API boundary change.
    - No new HTTP route, schema, or ingest rewrite.
* Insights
    - Existing exact message-dict assertion in `test_session_detail_reconstructs_ordered_messages_and_nested_tools` must gain `subagents: []` and `parent_spawn: null` in the same TDD step.

## 2026-08-26 - PREFLIGHT - COMPLETE (FAIL (blocking))

* Work completed
    - Validated the plan's TDD ordering, file conventions, dependency impacts, fragment navigation, exports, and association inputs against the current dashboard implementation.
    - Wrote `FAIL (blocking)` to `.preflight-status`.
* Decisions made
    - Build is gated until the session-render unit has a real test-first path and the association, hashchange, export, Claude fallback, and composite-identity gaps are resolved in the plan.
* Insights
    - `associate_children(harness, tools, children)` cannot implement the no-tool “last message” fallback without parent message information.
    - The current hashchange listener accepts only `#msg-N`, and the JSON exporter serializes the complete session-detail payload; both are integration surfaces the plan omitted.

## 2026-08-26 - PREFLIGHT - OPERATOR GUIDANCE

* Decisions made
    - Claude unmatched `spawning_tool_use_id`: refuse to guess; no leftover pill.
    - JSON export keeps the new fields; do not redact.

## 2026-08-26 - PLAN - IN-PROGRESS (re-plan after blocking preflight)

* Work completed
    - Operator guidance recorded; re-entering Plan to encode the blocking findings.
