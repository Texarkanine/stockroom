---
task_id: dashboard-freshness-cache
complexity_level: 3
date: 2026-07-31
status: completed
---

# TASK ARCHIVE: Dashboard Freshness Cache

## SUMMARY

Added an in-process dashboard API response cache keyed by warehouse file fingerprint `(mtime_ns, size)` so browser refresh skips DuckDB open+query when the warehouse is unchanged, while still invalidating for ingest and backfill without writer hooks or `_sync_state` alone. Live UAT then drove two Level 1 reworks under the same task id: session deep-link boot no longer fans out unused metrics `/api/*` calls, and `ResponseCache` became a hard-capped LRU (default 64) so a long-lived process cannot grow unbounded within one warehouse epoch. Shipped via draft [PR #113](https://github.com/Texarkanine/stockroom/pull/113) on `cache-dash`.

## REQUIREMENTS

From the project brief:

1. Investigate why dashboard refresh is still slow when nothing new has been ingested and a high watermark already exists.
2. Cache dashboard API data so unchanged warehouse freshness does not force full regeneration.
3. Invalidation must cover ingest (watermark advancement) and backfill (which does not touch `_sync_state`).
4. Preserve read-only dashboard contracts: no migrate, offline local UI, existing JSON status codes.

Out of scope for the L3 brief: ingest/backfill CLI changes; embedding UX; browser-only workarounds that ignore server-side freshness; CDN / multi-machine cache.

**Rework (UAT efficiency):** Conversation-detail boot (`?view=session&…`) must fetch only `/api/session`, not the metrics snapshot fan-out. Keep correct metrics load for metrics home (and justified sessions-list harness discovery). Keep the server cache; stop asking for unused endpoints.

**Rework (cache bound):** Bound in-epoch cache growth with a simple hard entry cap / LRU. Metrics-home warm hits must stay cheap. Conversation misses are acceptable. Fingerprint clear-all and API contracts unchanged. No per-endpoint special cases unless a global cap is insufficient.

## CREATIVE PHASE DECISIONS

**Design question:** where does the cache live, and what freshness signal invalidates it for both ingest and backfill?

**Options evaluated:**

- **A · Server in-process cache + warehouse file fingerprint (`mtime_ns`, `size`):** Cache successful JSON on the server; clear when `stat()` fingerprint drifts.
- **B · Server cache keyed only on `_sync_state` / watermark:** Reuse `max(updated_at)` as the epoch.
- **C · Explicit invalidation hooks in ingest + backfill:** Writers notify or clear a shared token.
- **D · Client persistence and/or HTTP `ETag`/`Cache-Control` alone:** Browser-side or conditional GET without skipping server compute on hard refresh.

**Selected: Option A.** Watermark-only (B) is eliminated by the product invariant that backfill must not move `_sync_state`. Writer hooks (C) couple packages and risk silent staleness on missed writers. Client/HTTP-only (D) does not stop server recompute on hard refresh against a long-lived local process. Verified: DuckDB writes bump `st_mtime_ns` and `st_size`; read-only opens do not. False invalidation after embed/migrate is rare and correctness-preserving.

**Tradeoffs accepted:** Conservative false invalidation after unrelated warehouse writers; cold cache after dashboard process replace/restart. Creative deferred ETag and optional LRU for later — correct for MVP, but the unbound in-epoch map became a memory landmine once the process was long-lived (closed by the bound rework without abandoning Option A).

**Friction discovered in implementation / UAT:** Creative did not surface the SPA boot fan-out; that appeared once the cache made unused metrics fetches obvious on session deep-links. Writer-connection flock is held until connection GC/`weakref.finalize`, not `close()` — a test self-deadlock, not a product design failure.

## IMPLEMENTATION

**Feature (L3):**

- **`stockroom.dashboard.cache`:** Thread-safe `ResponseCache` with warehouse fingerprint `(mtime_ns, size)`, shared `canonical_request_key`, hit path that skips `open_warehouse` (proven via injectable opener counter). Cache only successful 200 JSON bodies; 400/404/503 unchanged.
- **Server wiring:** On API GET, fingerprint warehouse path; hit returns cached body; miss computes, stores; fingerprint drift clears all entries.
- **Invalidation proof:** Ingest-shaped and backfill-shaped (no-watermark) warehouse writes bump fingerprint and miss after clear; no ingest/backfill module changes.
- **Docs / patterns:** User-guide, architecture lifecycle, contributing iteration notes; `systemPatterns.md` warehouse/dashboard cache sentence.
- **Key files:** `skills/sr-search/src/stockroom/dashboard/cache.py`, `server.py` wiring, `tests/test_dashboard_cache.py`, dashboard docs under `docs/`.

**Rework (L1 efficiency):**

- `shouldRefreshMetricsOnBoot` + gated boot `refreshDashboard` in `dashboard.mjs` — false for valid `view=session` deep-links so only `/api/session` loads.
- Sessions-list boot still refreshes metrics (harness discovery) — intentional, left as-is.
- JS unit test added; server cache remains complementary for metrics home.

**Rework (L1 cache bound):**

- `ResponseCache(max_entries=64)` default (`DEFAULT_MAX_ENTRIES`); `OrderedDict` LRU — get/put move to MRU; put evicts LRU when over cap.
- Fingerprint drift still clear-all.
- Docs note bounded LRU; global entry cap only (no per-endpoint special cases). Metrics-home fan-out stays well under 64; conversation browsing is what the cap bounds.

**PR feedback during review:** Sticky-stale risk when a concurrent put used a post-query fingerprint after drift — fixed by threading the pre-query fingerprint from `get` into `put` ([PR #113](https://github.com/Texarkanine/stockroom/pull/113)).

## TESTING

- TDD for L3: cache unit/integration tests ahead of server wiring; injectable opener counter for hit/miss; concurrency and non-200 paths covered. Preflight amended plan with shared `canonical_request_key`.
- Live measure on ~14GB warehouse: ~30d metrics fan-out cold ~0.83s → warm ~0.018s (~47×); page feel after warm API still SPA/Chart-bound.
- L1 efficiency: 120 JS passed; full pytest 808 passed / 4 skipped at that checkpoint.
- L1 bound: eviction, get-refresh MRU, and finite default unit tests; suite 811 pytest (+4 skipped), 120 JS, ruff clean.
- `/niko-qa` PASS for L3, efficiency rework, and bound rework (trivial user-guide “bounded LRU” wording fix on the last pass).
- Operator UAT drove both reworks (network fan-out on session refresh; unbounded memory concern).

## LESSONS LEARNED

- Writer connections from `warehouse.open(read_only=False)` release the coordination flock via `weakref.finalize` on the connection object. Keeping a closed connection bound to a name blocks the next writer open indefinitely. Prefer a nested helper (or `del`) before reopening for write in long-lived test scopes (e.g. while a dashboard server is up).
- A warm server cache does not fix a wrong client boot path: session deep-links were still paying for a full metrics fan-out (then hitting cache). Omit unused fetches first; cache what the view still needs.
- Cold pain on a ~14GB warehouse is DuckDB open+query; warm API ~18ms. After that, page feel is SPA/Chart-bound — further API caching has diminishing UX return vs front-end work.
- An unbounded in-process response map is a landmine for week-long dashboard processes; a hard entry LRU is enough. Plugin-update bounce kills the process and clears the heap; fingerprint drift clear-all still drops the whole epoch.
- Deferred “optional LRU” from creative is fine for MVP only if a second pass asks whether the cache itself can grow without limit.

## PROCESS IMPROVEMENTS

- Performance tasks that stop at “add a cache” risk shipping correct caching of unnecessary work *and* unbounded retention. UAT should watch the network panel for the target view; a second pass should ask whether the cache itself can grow without limit.
- L3 → operator UAT/rework → L1s under the same task id worked cleanly; archive should collapse all reflections rather than treating reworks as separate projects (and must not `rm -rf memory-bank/active` without archiving when creative/reflections exist).

## TECHNICAL IMPROVEMENTS

- Further dashboard feel wins are likely SPA/Chart-bound once the metrics API is warm — not more response caching.
- Sessions-list boot still prefetches metrics for harness discovery; revisit only if that path becomes a measured pain.

## NEXT STEPS

- Draft [PR #113](https://github.com/Texarkanine/stockroom/pull/113) on `cache-dash` — mark ready and merge when satisfied.
