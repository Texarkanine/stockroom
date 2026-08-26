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

## 2026-08-26 - PLAN - COMPLETE (re-plan after blocking preflight)

* Work completed
    - Encoded every blocking/high/medium preflight finding into the implementation units.
    - Added a testable transcript render model so sibling pills and the parent line have a red test before `dashboard.mjs` / `index.html` edits.
    - Amended both creatives so leftover, export, hashchange, and composite identity no longer contradict the plan.
* Decisions made
    - `associate_children(harness, tools, children, message_ordinals)` — leftover can use the last message when there are no tools.
    - Claude unmatched/missing spawn id: omit. Cursor leftover unchanged.
    - JSON export keeps the new fields; markdown stays pill-free.
    - Hashchange uses a generic fragment helper (`#msg-N` or `#msg-N-sa-M`).
    - `association_method` advisory declined for this task.
* Insights
    - The first plan's unit 4 had no failing render test because `dashboard.mjs` has no DOM harness. A pure item list in `dashboard-session.mjs` is the existing-suite way to specify sibling insertion.

## 2026-08-26 - PREFLIGHT - COMPLETE (PASS WITH ADVISORY)

* Work completed
    - Re-validated the repaired plan against the dashboard code: `session_detail`, `/api/session` dispatch, `dashboard-session.mjs` helpers, the `dashboard.mjs` hashchange/mount paths, the existing metrics and static tests, and the Cursor ingest slot rule.
    - Wrote `PASS WITH ADVISORY` to `.preflight-status`; no in-phase plan edits were needed.
* Decisions made
    - Build is unblocked. All five prior blocking/high/medium findings are encoded in the plan; the remaining eight findings are low-severity notes and one advisory.
* Insights
    - `ingest/sources.py` sorts child transcripts with `sorted(subagents_dir.glob("*.jsonl"))` and `_parent_subagent_types` walks messages then tool calls skipping untyped Tasks, so the planned `source_path` + typed-Task zip reproduces ingest's own slot list exactly.
    - `test_dashboard_static.py` gates resources, radios, and accessibility roles but not element ids, so `#session-parent` and `.session-subagent` add no static-contract work.
    - Existing in-app session links intercept clicks to keep SPA state; the planned plain anchors are a deliberate, functionally correct deviation worth naming in QA notes.

## 2026-08-26 - PLAN - OPERATOR GUIDANCE (no false-positive pills)

* Decisions made
    - A pill is a positive claim. Omit when uncorroborated. Missing a pill is acceptable.
    - Cursor leftover is forbidden. `associate_children` no longer takes `message_ordinals`.
    - Cursor places only via aligned zip (count + `agent_type`/`subagent_type` sequence) or unique `agent_type` pairs.
* Insights
    - A missing Task or child would shift an unchecked zip. Count+type catches that unless two compensating holes leave one shared type.

## 2026-08-26 - PREFLIGHT - COMPLETE (PASS WITH ADVISORY, ready for Build)

* Work completed
    - Preflight gate is `PASS WITH ADVISORY`. Operator invoked `/niko-build`.
* Decisions made
    - Build proceeds on the re-planned tasks.md (no leftover, corroborated zip, omit unknown harness).
* Insights
    - Association policy changed after the last preflight; the plan already encodes that. No `/niko-plan` re-gate.

## 2026-08-26 - BUILD - COMPLETE

* Work completed
    - Unit 1: `stockroom.dashboard.spawns` — provenance join, corroborated zip, unique-type rescue, omit unknown harness (12 tests).
    - Unit 2: `session_detail` always emits `messages[].subagents` and `parent_spawn`; queries keyed by `(harness, session_id)` (7 new payload tests, including two integration cases).
    - Unit 3: `#msg-N-sa-M` helpers, generic fragment parser, parent-line href, JSON keeps new fields, markdown stays pill-free.
    - Unit 4: `sessionTranscriptItems` / `sessionParentLine` model, then mount sibling pills and `parent:` in `dashboard.mjs` / `index.html`.
    - Unit 5: user-guide + techContext name both fragment forms.
    - Full suite green; live UAT on `:58018` for `604ead72-…` / `bc960b66-…`.
* Decisions made
    - Built to plan. Plain `<a>` full-reload for pill and `parent:` links. Verification server on **58018** so `:58008` was left alone.
* Insights
    - Live parent has a typed Task at msg 48 (one pill) and an untyped "Nudge L3 QA" Task at msg 55 (not a slot). Browser-tool click on `parent:` did not navigate; href + hash boot did.

## 2026-08-26 - QA - COMPLETE (PASS)

* Work completed
    - Reviewed the implementation against the re-planned requirements and both creative decisions across association, session payload, navigation, rendering, exports, and documentation.
    - Re-ran lint, format, and the full test suite: 133 JavaScript tests passed; 840 Python tests passed, 4 skipped.
* Decisions made
    - PASS with no blocking semantic findings. Build does not need to rerun.
* Insights
    - The implementation keeps the risk-bearing association policy isolated in a pure helper and adds no schema, ingest, HTTP route, or dependency surface.
    - Composite harness identity, stable `#msg-N` anchors, omit-if-uncorroborated placement, and loading-state parent cleanup all match the plan.

## 2026-08-26 - REFLECT - COMPLETE

* Work completed
    - Wrote `memory-bank/active/reflection/reflection-dashboard-subagent-pills.md`.
    - Reconciled persistent files: productContext and systemPatterns unchanged; techContext already named both fragment forms in Build unit 5.
* Decisions made
    - Archive is the next operator command (`/niko-archive`). No L4 milestones file.
* Insights
    - The first plan's leftover and untested `dashboard.mjs` mount would have shipped a guessed turn or a spawn hash that `hashchange` ignored. Preflight blocking those was the high-leverage phase.
    - An untyped parent Task is not a spawn slot. Omit-if-uncorroborated is the policy the tests now encode.

## 2026-08-26 - POST-REFLECT CHROME / PR

* Work completed
    - Operator live-look chrome: `SUB-AGENT` outer turn, inner convo pill, 1.5rem inset + accent tint, visible `#N-sa-M` ordinal.
    - Draft PR #126. Merged `origin/main` (kept spawn mount; wired `bindSessionMarkdown` from #123).
* Decisions made
    - In-IDE browser tools were crashy this session; verify by hard-refresh of `:58008`, not another worktree listener.
* Insights
    - `dashboard.mjs` is cached separately from inline `index.html` CSS — a CSS-only refresh can lie about JS chrome.

## 2026-08-26 - ARCHIVE - IN PROGRESS

* Work completed
    - Operator invoked `/niko-archive` with PR #126 chrome accepted.
* Decisions made
    - Category `enhancements/` — session reconstruction already existed; this extends it with spawn pills and parent deep-links.
* Insights
    - None beyond the reflection.

