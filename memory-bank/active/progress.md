# Progress

Add a Skill Usage dashboard capability per [#63](https://github.com/Texarkanine/stockroom/issues/63): harness-extensible extraction + API endpoint, then several aggregate/compare chart mockups in the main dashboard so the operator can pick a visual before final layout placement.

**Complexity:** Level 3

## 2026-07-17 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - Intent clarified and approved (count every discrete skill use; mockups in main dashboard at Tool Usage size)
    - Complexity classified as Level 3
* Decisions made
    - User 10 + agent 5 uses of the same skill = 10 and 5 counts (no session-level dedupe)
    - Mockup phase embeds candidates in the main dashboard (1×1 like Tool Usage); placement next to Tool Usage is a follow-up after chart selection
* Insights
    - Skill identity lives in heterogeneous `tool_calls` / message shapes — per-harness Python extractors over filtered SQL rows match existing ingest adapter style better than one mondo query
