# Progress

Investigate dashboard refresh cost when the warehouse is unchanged, then add caching so dashboard data is not regenerated on every page load unless ingest or backfill has written new content. Invalidation must cover ingest watermark advancement and backfill (which does not update `_sync_state`). Reworks: stop inefficient metrics fan-out on conversation-detail boot; bound the in-process response cache so it cannot grow unbounded within one warehouse epoch.

**Complexity:** Level 1

## 2026-07-30 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - Restated and confirmed intent (dashboard cache keyed on warehouse freshness; invalidate for ingest and backfill)
    - Classified as Level 3 Intermediate Feature
* Decisions made
    - Level 3: design needed for freshness signal because backfill deliberately leaves `_sync_state` untouched
* Insights
    - `metrics.py` already exposes `max(_sync_state.updated_at)` as last sync, but that alone is an insufficient invalidation key for backfill

## 2026-07-30 - CREATIVE - COMPLETE

* Work completed
    - Architecture creative for cache placement + freshness signal
    - Documented in `memory-bank/active/creative/creative-dashboard-cache-architecture.md`
* Decisions made
    - Server in-process response cache; fingerprint = warehouse `(mtime_ns, size)`; invalidate by clearing on fingerprint drift; no writer hooks
* Insights
    - Verified DuckDB writes bump mtime+size; read-only opens do not
    - Local warehouse ~14GB — explains refresh cost of open+query fan-out

## 2026-07-30 - PLAN - COMPLETE

* Work completed
    - Component analysis, TDD plan, ordered implementation steps, challenges, pre-mortem written to `tasks.md`
* Decisions made
    - Cache only successful 200 JSON bodies; normalize request keys; prove hits skip `open_warehouse` via injectable counter
* Insights
    - Backfill invalidation can be proven with a no-watermark warehouse write if full vscdb fixtures are too heavy for CI

## 2026-07-30 - PLAN - SAVED BEFORE PREFLIGHT

* Work completed
    - Plan finalized; transitioning to preflight validation

## 2026-07-30 - PREFLIGHT - COMPLETE

* Work completed
    - Validated TDD encoding, conventions, dependencies, conflicts, completeness
    - Wrote `.preflight-status` = PASS
    - Amended plan: shared `canonical_request_key`; architecture lifecycle docs in step 5
* Decisions made
    - No rearchitect; proceed to operator-gated build
* Insights
    - Existing “cache_*” metrics fields are LLM token counters, not a response cache to extend

## 2026-07-30 - BUILD - IN-PROGRESS

* Work completed
    - Operator invoked `/niko-build`; prerequisites verified (preflight PASS, plan complete, creative Option A)
* Decisions made
    - Proceed with creative Option A unchanged (file fingerprint + in-process ResponseCache)
* Insights
    - (none yet)

## 2026-07-30 - BUILD - COMPLETE

* Work completed
    - Implemented `dashboard/cache.py` + server hit/miss wiring; invalidation via warehouse file fingerprint; docs
    - Verification: 147 dashboard-py, 119 JS, 808 pytest (+4 skipped), ruff clean
* Decisions made
    - Cache only successful 200 JSON; shared `canonical_request_key` for query identity
* Insights
    - Writer-connection flock is released by GC/finalize, not `close()` — tests that reopen for write must drop the closed connection reference (nested helper) or they self-deadlock

## 2026-07-30 - QA - COMPLETE

* Work completed
    - Semantic review vs plan + creative Option A; completeness/KISS/YAGNI/docs checked
    - Trivial fixes: `RequestKey` typing on `ResponseCache`; surgical `systemPatterns.md` warehouse/dashboard cache sentence
    - Wrote `.qa-validation-status` = PASS; cache-focused tests re-run green
* Decisions made
    - Limit-parse duplication between server validation and `canonical_request_key` accepted (plan’s shared key helper; full parse extract is out of scope)
    - `invalidate_if_stale` kept (plan API; used by unit tests; get/put already drift-clear)
* Insights
    - None beyond build flock note

## 2026-07-30 - REFLECT - COMPLETE

* Work completed
    - Wrote `memory-bank/active/reflection/reflection-dashboard-freshness-cache.md`
    - Reconciled persistent files (systemPatterns already current from QA; product/tech unchanged)
* Decisions made
    - Archive is operator-gated next (`/niko-archive`)
* Insights
    - Writer flock held until connection GC/finalize — nested write helpers in tests that reopen while a server runs

## 2026-07-31 - REWORK - INITIATED

* Work completed
    - Operator chose rework over archive; goal reframed: make the dashboard faster by making it more efficient
* Operator feedback
    - UAT: refreshing a conversation detail page still fans out all metrics `/api/*` calls; those must not run on session view — only `/api/session` is needed
    - Root cause already identified in investigation: `dashboard.mjs` boot always calls `void refreshDashboard(true)` after `openSessionView`, even for `view=session` deep-links
    - Server cache is working (~0.8s → ~0.02s API fan-out when warm); remaining win is stop unnecessary work, not more caching of wrong fetches
* Decisions made
    - Keep task id `dashboard-freshness-cache`; clear plan/QA gates and re-classify for the efficiency rework

## 2026-07-31 - COMPLEXITY-ANALYSIS - COMPLETE (rework)

* Work completed
    - Classified rework as Level 1 Quick Bug Fix
* Decisions made
    - Single SPA component (boot routing in `dashboard.mjs` + pure helper); cause known; no architecture redesign
* Insights
    - Efficiency win is omit unnecessary fetches; server cache remains complementary for metrics home

## 2026-07-31 - BUILD - COMPLETE (rework)

* Work completed
    - `shouldRefreshMetricsOnBoot` + gated boot `refreshDashboard`; JS test added
    - Verification: 120 JS passed; full pytest 808 passed / 4 skipped
* Decisions made
    - Sessions-list boot still loads metrics (harness discovery) — out of this fix’s change set
* Insights
    - Same inefficiency class as caching: do not run work the current view does not need

## 2026-07-31 - QA - COMPLETE (rework)

* Work completed
    - Semantic review: fix matches rework brief; no over-engineering; docs N/A for boot gating
    - Wrote `.qa-validation-status` = PASS; brief L1 reflection for archive collapse
* Decisions made
    - Leave sessions-list metrics prefetch as-is (justified by harness discovery)
* Insights
    - Prefer omit unnecessary fetches over caching them

## 2026-07-31 - REFLECT - COMPLETE (L3 + L1 rework)

* Work completed
    - Rewrote `reflection-dashboard-freshness-cache.md` to cover full lifecycle (L3 cache + UAT + L1 efficiency rework)
    - Kept brief `reflection-dashboard-freshness-cache-rework.md` for archive collapse
    - Reconciled persistent files: no further edits (systemPatterns already had cache sentence)
* Decisions made
    - Same task id; archive collapses both reflections; next step is operator-gated `/niko-archive`
* Insights
    - Warm cache exposed unused SPA boot fan-out; omit-then-cache is the performance ordering that mattered

## 2026-07-31 - REWORK - INITIATED (cache bound)

* Work completed
    - Operator chose rework over archive; unbounded in-epoch cache is a memory landmine
* Operator feedback
    - Caching without a bound can grow forever while exploring within one warehouse epoch
    - Hard entry cap or LRU is fine — do not over-engineer; guarantee it cannot take all memory
    - Aggressive eviction OK; cache misses fine (esp. unfamiliar conversation pages)
    - Hot path that must stay cheap: main metrics dashboard refresh/reload
    - Nightly ingest / fingerprint drift still clear-all; plugin-update bounce kills the process (heap gone)
* Decisions made
    - Keep task id `dashboard-freshness-cache`; clear plan/QA gates and re-classify for the bound

## 2026-07-31 - COMPLEXITY-ANALYSIS - COMPLETE (cache bound)

* Work completed
    - Classified as Level 1 Quick Bug Fix
* Decisions made
    - Single component (`ResponseCache`); hard max-entry / LRU; no architecture redesign
* Insights
    - Metrics-home warm hits matter; conversation misses are acceptable collateral of a tight cap

## 2026-07-31 - BUILD - IN-PROGRESS (cache bound)

* Work completed
    - Leaving complexity analysis; starting Level 1 build for max-entry LRU bound

## 2026-07-31 - BUILD - COMPLETE (cache bound)

* Work completed
    - `ResponseCache` max-entry LRU (`DEFAULT_MAX_ENTRIES = 64`); get refreshes MRU
    - Tests for eviction, get-refresh, finite default; docs + systemPatterns note
    - Verification: 811 pytest (+4 skipped), 120 JS, ruff clean
* Decisions made
    - Global entry cap only — no per-endpoint special cases
* Insights
    - Metrics-home fan-out stays well under 64; conversation browsing is what the cap bounds

## 2026-07-31 - QA - COMPLETE (cache bound)

* Work completed
    - Semantic review vs rework brief: bound, metrics-home warm path, fingerprint clear-all, no special cases
    - Trivial fix: user-guide dashboard.md “bounded LRU” wording
    - Wrote `.qa-validation-status` = PASS
* Decisions made
    - `DEFAULT_MAX_ENTRIES = 64` accepted (named constant; metrics fan-out ≪ cap)
* Insights
    - Nothing beyond build

## 2026-07-31 - NK-SAVE (reflections + PR sync)

* Work completed
    - Updated combined reflection for L3 + efficiency + bound; added `reflection-dashboard-freshness-cache-bound.md`
    - PR #113 body/title refreshed for LRU bound; branch pushed

## 2026-07-31 - ARCHIVE - IN-PROGRESS

* Work completed
    - Operator invoked `/niko-archive` to collapse L3 + both L1 reflections under the same task id
* Decisions made
    - Route as Level 3 archive (original complexity + creative/reflections present); do not `rm -rf memory-bank/active` without archiving
