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
