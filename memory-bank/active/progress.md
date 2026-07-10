# Progress

Fix warehouse/dashboard timezone skew ([issue #32](https://github.com/Texarkanine/stockroom/issues/32)): store all DB timestamps as UTC; clients render into a timezone. Align ingest (`source_mtime`, Claude authored times), metrics activity clock, and dashboard display so Claude and Cursor wall-clock times match.

**Complexity:** Level 2

## 2026-07-10 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - Validated intent against issue #32 with operator confirmation (UTC-in-DB, client-side zone rendering)
    - Classified as Level 2 (bug fix, multiple components: ingest, metrics, dashboard)
* Decisions made
    - Timezone contract: all warehouse timestamps are UTC; clients own timezone display
* Insights
    - Root skew is mixed naive clocks: Claude `started_at` is UTC-as-naive; `source_mtime` is local-naive; UI treats ISO without zone as local

## 2026-07-10 - PLAN - READY

* Work completed
    - Complexity analysis archived; entering plan phase
* Decisions made
    - Proceeding to Level 2 plan per workflow
