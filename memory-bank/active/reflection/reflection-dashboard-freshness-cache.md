---
task_id: dashboard-freshness-cache
date: 2026-07-30
complexity_level: 3
---

# Reflection: dashboard-freshness-cache

## Summary

Shipped an in-process dashboard API response cache keyed by warehouse file `(mtime_ns, size)` plus canonical request identity, so browser refreshes skip DuckDB open/query when nothing has been written. Build and QA passed with no plan deviations.

## Requirements vs Outcome

All project-brief use cases landed: unchanged refresh hits cache; ingest invalidates; backfill-shaped writes (no `_sync_state` move) invalidate via file fingerprint. Public JSON contracts and 400/404/503 behavior preserved; only successful 200 bodies are cached. No scope creep (no ETag/LRU/writer hooks).

## Plan Accuracy

The six-step plan matched reality: new `dashboard/cache.py`, server wiring, invalidation tests, error/concurrency tests, docs, full-suite verification. Preflight’s shared `canonical_request_key` amendment prevented query-key drift. Challenges that mattered were the ones anticipated (normalize harness/scalars; prove hits skip opener; backfill via no-watermark write). The only local surprise was a test self-deadlock on the writer flock — not a plan gap in the product design.

## Creative Phase Review

Option A (server cache + file fingerprint) held up cleanly: DuckDB writes bump mtime/size; read-only opens do not; no ingest/backfill coupling required. Watermark-only (B) correctly rejected; writer hooks (C) unnecessary. Implementation notes (clear-all on drift, cache 200s only, optional ETag deferred) mapped 1:1 into code.

## Build & QA Observations

TDD flow was straightforward; injectable opener counter made hit/miss assertions crisp. One hung test during invalidation work traced to `warehouse.open` holding `fcntl.flock` until the connection is GC’d (`weakref.finalize`), not until `close()` — fixed by nesting the writer so the closed connection drops out of scope. QA was clean aside from typing polish and a surgical `systemPatterns` sentence.

## Cross-Phase Analysis

Creative’s rejection of watermark-only made the backfill invalidation test an acceptance criterion rather than an afterthought — that chain worked. Preflight’s canonical-key amendment avoided a class of cache-key bugs without rearchitecting. No creative→QA friction; the flock gotcha was test hygiene against an existing warehouse invariant, not a design miss.

## Insights

### Technical
- Writer connections from `warehouse.open(read_only=False)` release the coordination flock via `weakref.finalize` on the connection object. Keeping a closed connection bound to a name blocks the next writer open indefinitely. Prefer a nested helper (or `del`) before reopening for write in long-lived test scopes (e.g. while a dashboard server is up).

### Process
- Nothing notable — L3 creative → plan → preflight → build → QA fit this feature; operator-gated build was the right checkpoint after the freshness-signal design choice.
