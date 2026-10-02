# Progress

Put `session_id` and `message_id` on every `stockroom semantic` result so a hit can be opened with `stockroom query` without running the search again, and update the `sr-semantic` skill to match.

**Complexity:** Level 2

## 2026-10-02 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - Restated the output-contract change and got operator confirmation.
    - Classified the task as Level 2 and wrote the ephemeral memory-bank files.
* Decisions made
    - Level 2: a self-contained enhancement of the semantic render contract plus the skill that documents the handoff. Not a crash fix, and not a multi-component feature.
* Insights
    - The identifiers already exist on each hit and already appear in `--format json`. The default `tsv` and `table` shapes omit them via `_SEMANTIC_COLUMNS`.

## 2026-10-02 - PLAN - COMPLETE

* Work completed
    - Wrote the Level 2 plan: render columns plus the skill and CLI-page handoff.
* Decisions made
    - Keep `tsv` as the default. Add `session_id` and `message_id` after `harness` and before `role`, matching JSON field order. Leave the JSON payload and preview truncation alone.
    - Treat `skills/sr-semantic/SKILL.md` and the foreign-key tip in `docs/advanced/cli.md` as required prose, not a follow-up.
* Insights
    - `docs/advanced/cli.md` currently tells humans that only `--format json` carries a foreign key. That page would keep teaching the old UX if the renderer changed alone.
