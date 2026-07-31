---
task_id: dashboard-freshness-cache
date: 2026-07-31
complexity_level: 3
---

# Reflection: dashboard-freshness-cache

## Summary

Shipped an in-process dashboard API response cache keyed by warehouse file `(mtime_ns, size)`, then closed two follow-ups from live use: session deep-link boot no longer fans out metrics, and the cache is a hard-capped LRU (default 64) so a long-lived process cannot grow unbounded within one warehouse epoch.

## Requirements vs Outcome

**L3 (original brief):** Unchanged refresh hits cache; ingest invalidates; backfill-shaped writes invalidate via file fingerprint without relying on `_sync_state`. Public JSON contracts and 400/404/503 preserved; only successful 200 bodies cached. No ETag/writer hooks.

**L1 rework (UAT efficiency):** Conversation-detail boot (`?view=session&…`) fetches only `/api/session`, not the metrics fan-out. Sessions-list boot still refreshes metrics (harness discovery) — intentional. Server cache kept for metrics home.

**L1 rework (cache bound):** `ResponseCache` is max-entry LRU (`DEFAULT_MAX_ENTRIES = 64`); get refreshes MRU; put evicts LRU when over cap; fingerprint drift still clear-all. Metrics-home warm hits stay under the cap; conversation browsing is what the bound limits.

Nothing from the brief was dropped; the reworks added efficiency and a memory ceiling that UAT/review proved were missing from “cache alone.”

## Plan Accuracy

The six-step L3 plan matched reality: `dashboard/cache.py`, server wiring, invalidation tests, error/concurrency tests, docs, full-suite verification. Preflight’s shared `canonical_request_key` amendment prevented query-key drift. Anticipated challenges (normalize harness/scalars; prove hits skip opener; backfill via no-watermark write) were the ones that mattered. Local surprise was test self-deadlock on writer flock — product design was fine.

Both L1 reworks had no separate plan: known causes, single-component fixes (`shouldRefreshMetricsOnBoot`; `OrderedDict` LRU + `max_entries`).

## Creative Phase Review

Option A (server cache + file fingerprint) held up: DuckDB writes bump mtime/size; read-only opens do not; no ingest/backfill coupling. Watermark-only (B) correctly rejected; writer hooks (C) unnecessary. Creative deferred ETag/LRU as optional — correct for the first ship, but an unbounded in-epoch map is a memory landmine once the process is long-lived; the bound rework closed that gap without abandoning Option A.

Creative also did not surface the SPA boot fan-out — that appeared in live UAT once the cache made unused fetches obvious.

## Build & QA Observations

**L3:** TDD with injectable opener counter made hit/miss crisp. Hung invalidation test traced to `warehouse.open` holding `fcntl.flock` until connection GC (`weakref.finalize`), not `close()`. Live measure: ~30d fan-out cold ~0.83s → warm ~0.018s; page feel still SPA/Chart-bound after API was warm.

**L1 efficiency:** Boot gate + JS test; QA PASS; sessions-list metrics prefetch left intentional.

**L1 bound:** Three unit tests (evict LRU, get refreshes order, finite default); docs note bounded LRU; QA PASS with trivial user-guide wording fix. Suite: 811 pytest (+4 skipped), 120 JS.

## Cross-Phase Analysis

Creative’s rejection of watermark-only made the backfill invalidation test an acceptance criterion — that chain worked. Preflight’s canonical-key amendment avoided a class of cache-key bugs without rearchitecting.

Causal chains from live use: (1) L3 cached expensive metrics → UAT showed session boot still requesting them → omit the fan-out. (2) Unbounded cache is correct caching of every explored key → operator called the memory landmine → hard LRU cap. Caching first made both problems visible.

## Insights

### Technical
- Writer connections from `warehouse.open(read_only=False)` release the coordination flock via `weakref.finalize` on the connection object. Keeping a closed connection bound to a name blocks the next writer open indefinitely. Prefer a nested helper (or `del`) before reopening for write in long-lived test scopes (e.g. while a dashboard server is up).
- A warm server cache does not fix a wrong client boot path: session deep-links were still paying for a full metrics fan-out (then hitting cache). Omit unused fetches first; cache what the view still needs.
- Cold pain on a ~14GB warehouse is DuckDB open+query; warm API ~18ms. After that, page feel is SPA/Chart-bound — further API caching has diminishing UX return vs front-end work.
- An unbounded in-process response map is a landmine for week-long dashboard processes; a hard entry LRU is enough. Plugin-update bounce kills the process and clears the heap; fingerprint drift clear-all still drops the whole epoch.

### Process
- Performance tasks that stop at “add a cache” risk shipping correct caching of unnecessary work *and* unbounded retention. UAT should watch the network panel for the target view; a second pass should ask whether the cache itself can grow without limit.
- L3 → operator UAT/rework → L1s under the same task id worked cleanly; archive should collapse all reflections rather than treating reworks as separate projects.
