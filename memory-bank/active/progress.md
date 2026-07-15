# Progress

Implement surgical embedding invalidation on ingest session rewrite (compare-and-keep by message text) per https://github.com/Texarkanine/stockroom/issues/43 — stop cascade-deleting all session vectors when only append-only or unchanged history is rewritten.

**Complexity:** Level 2

## 2026-07-14 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - Intent clarified and approved against issue #43
    - Classified as Level 2: Simple Enhancement (self-contained change in ingest writer + tests; proposed solution already selected)
* Decisions made
    - Proceed with issue option B (text compare / compare-and-keep); no schema migration
* Insights
    - Failure mode is ingest eager cascade + embed lag, not embed itself wiping vectors
