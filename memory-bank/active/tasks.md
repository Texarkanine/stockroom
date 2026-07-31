# Task: dashboard-freshness-cache (rework)

* Task ID: dashboard-freshness-cache
* Complexity: Level 1
* Type: bug fix / efficiency rework

## What broke

Conversation-detail deep-links (`?view=session&…`) still ran the full metrics `fetchSnapshot` fan-out on every page load/refresh.

## Why

`dashboard.mjs` boot always executed `void refreshDashboard(true)` after `openSessionView`, regardless of view. `syncViewFromLocation` already skipped metrics when entering session; boot did not.

## Fix

- Added `shouldRefreshMetricsOnBoot(searchParams)` — false only for valid session deep-links.
- Boot calls `refreshDashboard` only when that returns true.
- Sessions-list boot still refreshes metrics (harness controls discover from overview) — intentional, not changed.

## Files

- `skills/sr-search/src/stockroom/dashboard/static/dashboard-session.mjs`
- `skills/sr-search/src/stockroom/dashboard/static/dashboard.mjs`
- `skills/sr-search/tests-js/dashboard-session.test.mjs`

## Status

- [x] Build
- [ ] QA
