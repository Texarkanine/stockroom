# Task: dashboard-freshness-cache (cache bound)

* Task ID: dashboard-freshness-cache
* Complexity: Level 1
* Type: bug fix / memory bound

## What broke

`ResponseCache` could grow without limit within one warehouse fingerprint epoch — a memory landmine for a long-lived dashboard while exploring.

## Why

Clear-all only runs on fingerprint drift; nothing capped entry count inside an epoch.

## Fix

- `ResponseCache(max_entries=64)` default; `OrderedDict` LRU — get/put move to MRU; put evicts LRU when over cap.
- Fingerprint drift still clear-all.
- Docs note bounded LRU.

## Files

- `skills/sr-search/src/stockroom/dashboard/cache.py`
- `skills/sr-search/tests/test_dashboard_cache.py`
- `docs/user-guide/dashboard.md`
- `docs/architecture/lifecycle.md`
- `docs/contributing/iteration/dashboard.md`
- `memory-bank/systemPatterns.md`

## Status

- [x] Build
- [ ] QA
