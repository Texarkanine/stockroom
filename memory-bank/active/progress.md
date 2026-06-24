# Progress

Milestone 1 of the `p1-data-backbone` L4 project: **Schema field enumeration + locked DDL**. Point an agent at real Cursor and Claude Code transcripts side by side, enumerate every field each format exposes, then lock one shared, harness-labeled set of tables (sessions, messages, tool calls inputs-only, plan documents, embeddings, sync-state watermark) encoding the stable message-identity contract and the conversation-reconstruction keys. Authored test-first against real and pathological fixtures, with the DDL written directly as the `0001` migration file and the enumeration evidence + shared fixtures committed as durable artifacts.

**Complexity:** Level 3

## 2026-06-24 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - Re-entered `/niko` on the `p1-data-backbone` L4 project in the "Not started" state (milestones.md present, no sub-run yet classified).
    - Classified the first unchecked milestone (Schema field enumeration + locked DDL) as **Level 3**, matching the L4 plan/preflight advisory estimate.
    - Created sub-run ephemeral files (this `progress.md`, stubbed `tasks.md`, refreshed `activeContext.md`); preserved the L4 `projectbrief.md` and `milestones.md`.
* Decisions made
    - L3, not L4: a complete feature across multiple cooperating components (two-format empirical enumeration, multi-table contract authored as migration `0001`), but the architecture is already fixed by the L4 plan — this sub-run produces one cohesive artifact set, not new subsystems.
* Insights
    - Operator override in effect: regardless of level, once the initial schema is drafted, STOP for operator review of (a) every field that exists in both harnesses and (b) the recommended kept subset. This maps to the L3 Plan → Creative path, where the schema is the open question and a draft pending sign-off is a legitimate "stop for operator" creative outcome.

## 2026-06-24 - PLAN/CREATIVE (schema enumeration) - STOPPED FOR REVIEW

* Work completed
    - Located on-disk data for both harnesses and ran a key-path enumerator over the full corpus (Cursor: 713 files / 25,065 records; Claude: 39 files / 4,158 records). Raw evidence committed under `memory-bank/active/creative/evidence/`.
    - Authored `creative/creative-schema-enumeration.md`: complete two-harness field enumeration with per-field KEEP/DERIVE/ENRICH/DROP dispositions, the subagent-linkage + message-identity analysis, an illustrative 6-table schema sketch, and 6 open questions.
* Decisions made (provisional, pending operator sign-off)
    - Stored content is tool **inputs only**; Claude `tool_result`/`toolUseResult` and all token-usage subtrees are DROP (token/cost is a v1 exclusion).
    - Cursor has no native ids/parent/model/timestamp → the message-identity contract mints deterministic surrogates for Cursor and adopts native `uuid`/`parentUuid` for Claude; `model`/`ts` are NULLable (enriched at ingest).
    - Subagent↔parent is field-based for Claude (`agentId` + `meta.json.toolUseId`) but structural-only for Cursor (`subagents/` containment).
* Insights
    - The two on-disk formats are radically asymmetric: Claude is self-describing; Cursor's transcript is a bare `role`/`message` list. The shared harness-labeled schema absorbs this by making Claude-native columns nullable/synthesized for Cursor.
    - `plan_documents` has no distinct on-disk record in either harness — its populating source is the weakest-grounded part of the brief's table list (open question Q3).
    - DDL deliberately NOT locked; awaiting operator review before authoring `migrations/0001` test-first.
