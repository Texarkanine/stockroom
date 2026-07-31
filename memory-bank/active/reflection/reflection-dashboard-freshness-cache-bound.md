---
task_id: dashboard-freshness-cache
date: 2026-07-31
complexity_level: 1
---

# Reflection: dashboard-freshness-cache (cache bound)

## Summary

Capped `ResponseCache` at a hard max-entry LRU (default 64) so one warehouse fingerprint epoch cannot grow unbounded while the user explores.

## What broke / fix

Clear-all only on fingerprint drift; no in-epoch cap. Added `max_entries` + `OrderedDict` LRU (get/put refresh MRU; put evicts LRU when over cap).

## Insight

Deferred “optional LRU” from creative is fine for MVP, but shipping an unbounded cache is shipping a memory landmine — a hard cap is the smallest guarantee that matters.
