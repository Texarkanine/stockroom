# Project Brief

## User Story

As a stockroom dashboard user, I want a browser refresh to reuse already-loaded dashboard data when the warehouse has not changed, so that I am not waiting on full regeneration when nothing new has been ingested or backfilled.

## Use-Case(s)

### Use-Case 1: Refresh with unchanged warehouse

The dashboard has already loaded. No ingest or backfill has written new data. The user refreshes the page. The dashboard should serve quickly from cache rather than recomputing everything from scratch.

### Use-Case 2: Refresh after ingest

New data has been ingested (watermark / sync state advanced, warehouse content updated). The next dashboard load must reflect the new data — cache must not serve stale metrics.

### Use-Case 3: Refresh after backfill

A one-shot backfill has written warehouse rows without advancing `_sync_state` watermarks. The next dashboard load must reflect the backfilled data — cache invalidation must not rely on watermark alone.

## Requirements

1. Investigate why a dashboard refresh still takes time when nothing new has been ingested and a high watermark already exists.
2. Implement caching for dashboard information so that once data is loaded and warehouse freshness is unchanged, a page load does not wait on regenerating that data.
3. Cache invalidation must account for ingest (including watermark advancement) and for backfill (which must not be missed even though backfill does not touch `_sync_state`).
4. Preserve existing dashboard contracts: read-only, no migrate, offline local UI.

## Out of Scope

1. Changing ingest or backfill scheduling / CLI UX.
2. Embedding, migration, or warehouse schema redesign beyond what caching/invalidation requires.
3. Browser-only workarounds that ignore server-side warehouse freshness.

## Rework

### Goal

Make the dashboard faster by making it more efficient — do less work on paths that do not need it, not only cache work that should not have run.

### Trigger (UAT)

Refreshing a conversation detail page (`view=session`) still issues the full metrics snapshot fan-out (`/api/overview`, trends, tools, …). That view only needs `/api/session`.

### Known cause

`dashboard.mjs` boot always runs `void refreshDashboard(true)` after opening a session deep-link. `syncViewFromLocation` already avoids that when navigating to session; boot does not.

### Rework requirements

1. Investigate efficiency gaps on dashboard load paths (session detail confirmed; check whether sessions-list boot has the same waste or a justified metrics prefetch).
2. Stop metrics snapshot fan-out on conversation-detail boot/refresh; fetch only what that view needs.
3. Preserve correct metrics load when entering/returning to the metrics home (and any path that still needs harness discovery).
4. Keep the existing server response cache; this rework complements it by not asking for unused endpoints.
