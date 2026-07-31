---
task_id: dashboard-freshness-cache
date: 2026-07-31
complexity_level: 3
---

# Reflection: dashboard-freshness-cache

## Summary

Shipped an in-process dashboard API response cache keyed by warehouse file `(mtime_ns, size)`, then after UAT closed an efficiency hole: session deep-link boot no longer fans out the metrics snapshot. Cache + omit-unused-work together match the real goal (faster dashboard), not just caching whatever the SPA asked for.

## Requirements vs Outcome

**L3 (original brief):** Unchanged refresh hits cache; ingest invalidates; backfill-shaped writes invalidate via file fingerprint without relying on `_sync_state`. Public JSON contracts and 400/404/503 preserved; only successful 200 bodies cached. No ETag/LRU/writer hooks.

**L1 rework (UAT):** Conversation-detail boot (`?view=session&…`) fetches only `/api/session`, not the metrics fan-out. Sessions-list boot still refreshes metrics (harness discovery) — intentional, left alone. Server cache kept as complementary for metrics home.

Nothing from the brief was dropped; the rework added the efficiency requirement that UAT proved was missing from “cache alone.”

## Plan Accuracy

The six-step L3 plan matched reality: `dashboard/cache.py`, server wiring, invalidation tests, error/concurrency tests, docs, full-suite verification. Preflight’s shared `canonical_request_key` amendment prevented query-key drift. Anticipated challenges (normalize harness/scalars; prove hits skip opener; backfill via no-watermark write) were the ones that mattered. Local surprise was test self-deadlock on writer flock — product design was fine.

The L1 rework had no separate plan (Level 1): cause was known from investigation (`dashboard.mjs` boot always `refreshDashboard(true)` after `openSessionView`). Fix was a pure `shouldRefreshMetricsOnBoot` gate aligned with `syncViewFromLocation`’s existing skip.

## Creative Phase Review

Option A (server cache + file fingerprint) held up: DuckDB writes bump mtime/size; read-only opens do not; no ingest/backfill coupling. Watermark-only (B) correctly rejected; writer hooks (C) unnecessary. Creative did not surface the SPA boot fan-out — that was outside the freshness-signal mega-unknown and only appeared in live UAT once the cache made API cost cheap enough that unused fetches stood out.

## Build & QA Observations

**L3:** TDD with injectable opener counter made hit/miss crisp. Hung invalidation test traced to `warehouse.open` holding `fcntl.flock` until connection GC (`weakref.finalize`), not `close()` — fixed by nesting the writer so the closed connection drops out of scope. QA clean aside from typing polish and a surgical `systemPatterns` sentence. Live measure: ~30d fan-out cold ~0.83s → warm ~0.018s; page feel still SPA/Chart-bound after API was warm.

**L1:** Small JS helper + boot gate; 120 JS + 808 pytest green. QA PASS with no substantive issues. Confirmed sessions-list metrics prefetch is justified, not the same bug.

## Cross-Phase Analysis

Creative’s rejection of watermark-only made the backfill invalidation test an acceptance criterion — that chain worked. Preflight’s canonical-key amendment avoided a class of cache-key bugs without rearchitecting.

The causal chain that mattered for the rework: L3 correctly cached expensive metrics work → UAT on session deep-links showed the SPA still requesting that work on every refresh → efficiency rework omitted the fetches. Caching first made the waste visible and measurable; without it, the fan-out cost was conflated with “warehouse is slow.” Process lesson: for performance work, UAT after the first win should ask “what work still runs that this view does not need?” not only “is the remaining work cached?”

## Insights

### Technical
- Writer connections from `warehouse.open(read_only=False)` release the coordination flock via `weakref.finalize` on the connection object. Keeping a closed connection bound to a name blocks the next writer open indefinitely. Prefer a nested helper (or `del`) before reopening for write in long-lived test scopes (e.g. while a dashboard server is up).
- A warm server cache does not fix a wrong client boot path: session deep-links were still paying for a full metrics fan-out (then hitting cache). Omit unused fetches first; cache what the view still needs.
- Cold pain on a ~14GB warehouse is DuckDB open+query; warm API ~18ms. After that, page feel is SPA/Chart-bound — further API caching has diminishing UX return vs front-end work.

### Process
- Performance tasks that stop at “add a cache” risk shipping correct caching of unnecessary work. Plan a UAT pass that watches the network panel for the target view, not only latency of cached endpoints.
- L3 → operator UAT → L1 rework under the same task id worked cleanly; archive should collapse both reflections rather than treating the rework as a separate project.
