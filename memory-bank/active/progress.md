# Progress

Fix warehouse/dashboard timezone skew ([issue #32](https://github.com/Texarkanine/stockroom/issues/32)): store all DB timestamps as UTC; clients render into a timezone. Align ingest (`source_mtime`, Claude authored times), metrics activity clock, and dashboard display so Claude and Cursor wall-clock times match.

**Complexity:** Level 2

## 2026-07-10 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - Validated intent against issue #32 with operator confirmation (UTC-in-DB, client-side zone rendering)
    - Classified as Level 2 (bug fix, multiple components: ingest, metrics, dashboard)
* Decisions made
    - Timezone contract: all warehouse timestamps are UTC; clients own timezone display
* Insights
    - Root skew is mixed naive clocks: Claude `started_at` is UTC-as-naive; `source_mtime` is local-naive; UI treats ISO without zone as local

## 2026-07-10 - PLAN - READY

* Work completed
    - Complexity analysis archived; entering plan phase
* Decisions made
    - Proceeding to Level 2 plan per workflow

## 2026-07-10 - PLAN - COMPLETE

* Work completed
    - Mapped UTC contract across discovery mtime, Claude `_parse_ts`, writer/metrics `now`, metrics JSON `Z`, dashboard parse/format, watermark-clear migration
    - Wrote TDD behaviors B1–B6 and ordered implementation steps in `tasks.md`
* Decisions made
    - DuckDB stays naive `TIMESTAMP` meaning UTC; wire format uses `Z`; no `TIMESTAMPTZ` migration
    - Clear `_sync_state` watermarks so re-ingest rewrites local `source_mtime`; do not SQL-convert historical observation times
    - Wrapped `peak_hour` remains UTC hour-of-day under this contract (local rebucket out of scope)
* Insights
    - UI-only fix would leave SQL windowing on mixed clocks; ingest + watermark reset are load-bearing
    - UTC+ offsets make watermark clear mandatory, not optional

## 2026-07-10 - PREFLIGHT - COMPLETE

* Work completed
    - Validated plan against codebase: existing `_iso`, schema test pattern, JS test surface (`dashboard-core.mjs`)
    - Amended plan: extend `_iso`; DML-only `0005`; update no-`Z` metric test pins
* Decisions made
    - Preflight PASS — proceed to build
* Insights
    - Recent Sessions bypassed `_iso` with raw `isoformat()` — fixing `_iso` alone is insufficient without routing `started` through it
