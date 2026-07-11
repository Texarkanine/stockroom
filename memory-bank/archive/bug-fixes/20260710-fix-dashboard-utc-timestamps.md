---
task_id: fix-dashboard-utc-timestamps
complexity_level: 2
date: 2026-07-10
status: completed
---

# TASK ARCHIVE: fix-dashboard-utc-timestamps

## SUMMARY

Fixed [issue #32](https://github.com/Texarkanine/stockroom/issues/32) by establishing a single timezone contract: warehouse timestamps are UTC-naive at rest; clients interpret them as UTC and render into a timezone. Claude Recent Sessions no longer skew from mixing UTC-as-naive `started_at` with local-naive `source_mtime` / JS local parsing. Build and QA passed; Claude and Cursor activity times share one clock.

## REQUIREMENTS

1. Persist all warehouse timestamps as UTC (naive UTC wall clock with a documented contract).
2. Clients own timezone display — interpret stored UTC and render into a zone when desired.
3. Fix Claude skew: do not mix UTC `started_at` with local `source_mtime` under `COALESCE`, and do not treat UTC hours as local in the UI.
4. Align other `started_at` / `source_mtime` / `ACTIVITY_TIME_SQL` consumers to the same contract.
5. Provide a migration/re-ingest path so existing local `source_mtime` values do not remain wrong under the new contract.

## IMPLEMENTATION

### Approach

DuckDB stays naive `TIMESTAMP` meaning UTC; wire format uses `Z`; no `TIMESTAMPTZ` migration. Shared `stockroom.timestamps` helpers (`utc_now`, `utc_from_timestamp`, `to_utc_naive`) feed discovery mtime, Claude `_parse_ts`, writer/metrics “now”, and metrics `_iso`. Migration `0005` is DML-only: clears `_sync_state` watermarks so the next ingest rewrites `source_mtime` under the UTC contract. Dashboard JS parses non-date-only values as UTC and formats with existing `Intl` local formatters. Wrapped `peak_hour` remains UTC hour-of-day (local rebucket out of scope).

### Key files

| Area | Files |
| --- | --- |
| UTC helpers | `skills/sr-search/src/stockroom/timestamps.py`, `tests/test_timestamps.py` |
| Discovery mtime | `ingest/sources.py`, `tests/test_ingest_sources.py` |
| Claude parse | `ingest/claude.py`, `tests/test_ingest_claude.py` |
| Writer / metrics now | `ingest/writer.py`, `dashboard/metrics.py` |
| Watermark reset | `migrations/0005_utc_timestamps.sql`, `tests/test_schema_0005.py` |
| Wire `Z` | `dashboard/metrics.py` (`_iso`), `tests/test_dashboard_metrics.py` |
| Client parse | `dashboard-core.mjs`, `tests-js/dashboard-time.test.mjs` |
| Patterns | `memory-bank/systemPatterns.md` (UTC-at-rest briefing) |

## TESTING

- TDD across B1–B6: UTC helpers, discovery mtime, Claude Z/offset stamps, `utc_now` call sites, watermark-clear migration, metrics `Z` wire format, dashboard UTC parse/format, date-only edge cases.
- Full suite: **491 passed, 3 skipped**; JS **36 passed**; `make format` / `make lint` clean.
- `/niko-qa` PASS; trivial hardening: `_iso` runs values through `to_utc_naive` before appending `Z`.
- Surprises were mostly test fallout: `_HEAD_VERSION` 4→5, and trends tests still monkeypatching `datetime.now` after call sites moved to `utc_now`.

## LESSONS LEARNED

### Technical

- When introducing a shared `utc_now`, every test that froze time via `datetime.now` must be updated in the same change — silent drift to real wall clock is easy to miss until the suite runs.
- Changing discovery mtime semantics without clearing `_sync_state` is unsafe on UTC+ machines; the DML-only migration was load-bearing, not optional cleanup.
- Wire-format helpers should assume callers may pass aware values even when the warehouse contract is naive UTC.

### Process

Nothing notable. Plan sequence held; preflight amendments (extend existing `_iso`, DML-only `0005`) were correct and cheap.

### Million-dollar question

If UTC-at-rest had been assumed from day one, `stockroom.timestamps` plus `_iso` / `parseDisplayDate` would still be the right shape — the elegant version is what we built, minus the one-shot watermark reset that only exists because local-naive mtimes shipped first.

## PROCESS IMPROVEMENTS

None — plan, preflight, build, QA, and reflect held without rework. Time-freeze tests coupling to the concrete clock helper name is worth remembering on the next clock-helper rename.

## TECHNICAL IMPROVEMENTS

None beyond the shipped contract. Optional future: client-side rebucket of wrapped `peak_hour` into local hour-of-day if operators want local peak display.

## NEXT STEPS

None. Task complete and archived. Operators should let the next ingest run after migration `0005` so `source_mtime` rewrites under the UTC contract.
