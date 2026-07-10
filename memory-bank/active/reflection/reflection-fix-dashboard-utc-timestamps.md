---
task_id: fix-dashboard-utc-timestamps
date: 2026-07-10
complexity_level: 2
---

# Reflection: fix-dashboard-utc-timestamps

## Summary

Fixed [issue #32](https://github.com/Texarkanine/stockroom/issues/32) by establishing UTC-at-rest for warehouse timestamps and teaching the dashboard to render them in the local zone. Build and QA passed; Claude/Cursor activity times now share one clock.

## Requirements vs Outcome

Delivered as specified: UTC storage (`source_mtime`, Claude stamps, `utc_now`), `Z` on the wire, client UTC parse, watermark-clear migration for safe re-ingest. No scope additions beyond labeling wrapped peak hour as UTC.

## Plan Accuracy

Plan sequence held. Real surprises were test fallout from the head version bump (`_HEAD_VERSION` 4→5) and trends tests that still monkeypatched `datetime.now` after call sites moved to `utc_now`. Watermark-clear challenge was correctly anticipated.

## Build & QA Observations

TDD cycles were straightforward. Full-suite failures were almost entirely pinned constants and time freezes, not product logic. QA only needed a small `_iso` hardening (`to_utc_naive` before `Z`).

## Insights

### Technical
- When introducing a shared `utc_now`, every test that froze time via `datetime.now` must be updated in the same change — silent drift to real wall clock is easy to miss until the suite runs.
- Changing discovery mtime semantics without clearing `_sync_state` is unsafe on UTC+ machines; the DML-only migration was load-bearing, not optional cleanup.

### Process
- Nothing notable

### Million-Dollar Question

If UTC-at-rest had been assumed from day one, `stockroom.timestamps` plus `_iso`/`parseDisplayDate` would still be the right shape — the elegant version is what we built, minus the one-shot watermark reset that only exists because local-naive mtimes shipped first.
