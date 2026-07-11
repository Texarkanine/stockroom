# Progress

Add a documented first-class CLI path so `stockroom query` / `stockroom semantic` can return message/`tool_input` text with whitespace matching DuckDB storage, instead of always collapsing newlines via `truncate_cell` ([issue #30](https://github.com/Texarkanine/stockroom/issues/30)).

**Complexity:** Level 2

## 2026-07-10 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - Validated intent against issue #30
    - Classified as Level 2 Simple Enhancement
    - Initialized ephemeral memory-bank files
* Decisions made
    - Level 2: self-contained change in truncate/render/CLI presentation; pick among issue's proposed directions during plan
* Insights
    - Current collapse-at-every-detail-level is intentional for table/TSV safety; the gap is missing an exact-text escape hatch, not a broken store
