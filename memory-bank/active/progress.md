# Progress

Investigate dashboard refresh cost when the warehouse is unchanged, then add caching so dashboard data is not regenerated on every page load unless ingest or backfill has written new content. Invalidation must cover ingest watermark advancement and backfill (which does not update `_sync_state`).

**Complexity:** Level 3

## 2026-07-30 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - Restated and confirmed intent (dashboard cache keyed on warehouse freshness; invalidate for ingest and backfill)
    - Classified as Level 3 Intermediate Feature
* Decisions made
    - Level 3: design needed for freshness signal because backfill deliberately leaves `_sync_state` untouched
* Insights
    - `metrics.py` already exposes `max(_sync_state.updated_at)` as last sync, but that alone is an insufficient invalidation key for backfill
