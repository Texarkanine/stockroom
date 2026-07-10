# Task: fix-dashboard-utc-timestamps

* Task ID: fix-dashboard-utc-timestamps
* Complexity: Level 2
* Type: bug fix
* Issue: https://github.com/Texarkanine/stockroom/issues/32

Establish a single timezone contract: all warehouse timestamps are UTC (naive DuckDB `TIMESTAMP` holding UTC wall clock). Clients interpret those values as UTC and render into a timezone when displaying. Fixes Claude Recent Sessions skew from mixing UTC-as-naive `started_at` with local-naive `source_mtime` / JS local parsing.

## Test Plan (TDD)

### Behaviors to Verify

- [B1]: File mtime discovery → `DiscoveredSession.mtime` / persisted `source_mtime` equal UTC-naive `datetime.fromtimestamp(st_mtime, tz=UTC).replace(tzinfo=None)`, not local `fromtimestamp` without tz
- [B2]: Claude ISO stamp with trailing `Z` (and offset-aware stamps) → `_parse_ts` yields UTC-naive datetime (convert via `astimezone(UTC)` before dropping tzinfo)
- [B3]: Writer / metrics “now” stamps (`_sync_state.updated_at`, default window end) → UTC-naive, not local `datetime.now()`
- [B4]: Metrics JSON activity / last-sync datetime strings → ISO-8601 with explicit UTC (`…Z` or `+00:00`) so clients do not treat them as local
- [B5]: Dashboard `parseDisplayDate` / `formatDate` on a UTC ISO datetime → renders in the runtime local zone (e.g. UTC `03:22` displays as prior-evening local on America/Chicago), not as 3:22 AM local
- [B6]: Migration after upgrade → `_sync_state` watermarks cleared (or equivalent) so next ingest rewrites `source_mtime` under the UTC contract; avoids UTC+ offset machines skipping sessions when comparing new UTC mtimes to old local watermarks
- [Edge: null activity]: Session with neither `started_at` nor `source_mtime` → Recent Sessions / activity consumers still omit or show em-dash without crashing
- [Edge: date-only labels]: Daily chart date-only strings remain calendar-day labels (local midnight parse OK); must not force-`Z` those
- [Regression]: Cursor-only rows (NULL `started_at`, UTC `source_mtime`) and Claude rows (`started_at` preferred) both sort/display on the same UTC activity clock

### Test Infrastructure

- Framework: pytest (`skills/sr-search/`, `make test`); Node 22 built-in test runner (`make test-js`, `tests-js/*.test.mjs`)
- Test location: `skills/sr-search/tests/`, `skills/sr-search/tests-js/`
- Conventions: `test_<module>.py` beside behavior; fixtures under `tests/fixtures/`; JS tests import from `dashboard-core.mjs` (export helpers under test)
- New test files: prefer extending `test_ingest_sources.py`, `test_ingest_claude.py`, `test_ingest_orchestrator.py`, `test_dashboard_metrics.py`, `test_schema_*.py`; add `tests-js/dashboard-time.test.mjs` (or extend core tests) for UTC parse/format; add `test_timestamps.py` only if a new shared helper module is introduced

## Implementation Plan

1. **Shared UTC helpers (TDD)**
   - Files: new `skills/sr-search/src/stockroom/timestamps.py` (or equivalent small module); `tests/test_timestamps.py`
   - Changes: `utc_now() -> datetime` (naive UTC); `utc_from_timestamp(epoch) -> datetime`; `to_utc_naive(dt) -> datetime`; document DuckDB TIMESTAMP = UTC contract in module docstring

2. **Discovery mtime → UTC (TDD)**
   - Files: `ingest/sources.py` (`_mtime`); `tests/test_ingest_sources.py`; `tests/test_ingest_orchestrator.py` (expectation currently uses local `fromtimestamp`)
   - Changes: `_mtime` uses UTC helper; update docstring (“naive-local” → “naive-UTC”)

3. **Claude `_parse_ts` → true UTC naive (TDD)**
   - Files: `ingest/claude.py`; `tests/test_ingest_claude.py` (add explicit Z / offset cases if fixtures don’t pin hours)
   - Changes: after `fromisoformat`, if aware → `astimezone(UTC).replace(tzinfo=None)`; leave naive as-is (treat as already UTC per contract)

4. **Stamp “now” as UTC (TDD)**
   - Files: `ingest/writer.py` (`update_sync_state`); `dashboard/metrics.py` (`parse_window`, daily effective_end); tests that assert `updated_at` / window defaults where practical
   - Changes: replace `datetime.now()` with `utc_now()`

5. **Watermark reset migration (TDD)**
   - Files: `migrations/0005_utc_timestamps.sql`; `tests/test_schema_0005.py` (behavior: watermarks cleared after apply). DDL unchanged vs `0004` — do **not** invent a divergent golden; either omit a new schema snapshot or assert introspection still matches the `0004` snapshot after applying through `0005`
   - Changes: `UPDATE _sync_state SET last_mtime = NULL, last_path = NULL` (keep rows) so next incremental acts like first run and rewrites `source_mtime`; document that existing `source_mtime` / `first_seen_at` local-naive values are corrected by re-ingest / only for new observations respectively

6. **API emits unambiguous UTC (TDD)**
   - Files: `dashboard/metrics.py` — extend existing `_iso` (do not add a parallel serializer); route Recent Sessions `started` through `_iso` instead of raw `activity.isoformat()`; `tests/test_dashboard_metrics.py` (update expectations currently pinned without `Z`, e.g. `last_sync` / `started`)
   - Changes: `_iso` appends `Z` for naive UTC datetimes; keep date-only / date.label strings as `YYYY-MM-DD` without time

7. **Dashboard client treats warehouse datetimes as UTC (TDD)**
   - Files: extract or export parse/format from `dashboard.mjs` into `dashboard-core.mjs` (tested surface); `tests-js/dashboard-time.test.mjs`; wire `dashboard.mjs` to shared helper
   - Changes: for non-dateOnly values, parse as UTC (`…Z` / offset, or append `Z` when timezone absent); format with existing `Intl` local formatters

8. **Docs / comments**
   - Files: `ingest/model.py` field docs; `metrics.py` module docstring (`ACTIVITY_TIME_SQL` “wall clock” → “UTC”); `migrations/0004` / `0005` comments; brief note in `docs/` or engine references if there is an existing ingest/dashboard time note
   - Changes: state the UTC-at-rest / client-renders-zone contract; note one-time full/incremental re-scan after migration; note wrapped `peak_hour` is UTC hour-of-day under this contract (local peak would require client rebucket — out of scope unless trivial)

9. **Verification**
   - Run targeted pytest modules, then `make test` / `make lint` / `make format` as required by build/preflight

## Technology Validation

No new technology - validation not required

## Dependencies

- Existing DuckDB naive `TIMESTAMP` columns (no type migration to `TIMESTAMPTZ` required if contract is UTC-naive + `Z` on the wire)
- Operator warehouse will re-scan sessions after watermark clear (one-time cost; idempotent writer)

## Challenges & Mitigations

- **Watermark skew on UTC+ machines**: Comparing new UTC mtimes to old local watermarks can skip work → Mitigation: migration clears watermarks (step 5)
- **Existing local `source_mtime` / `first_seen_at` rows**: Cannot losslessly convert without knowing historical offset → Mitigation: re-ingest fixes `source_mtime`; leave historical `first_seen_at` (not used by Recent Sessions “started”); document
- **`peak_hour` remains UTC hour**: Server buckets `.hour` on UTC-naive values → Mitigation: accept under UTC contract for L2; document; do not expand into TZ-aware server metrics
- **JS date-only vs datetime**: Blindly appending `Z` to date-only breaks daily charts → Mitigation: only UTC-normalize datetime strings (step 7 edge case)
- **Helper duplication**: Multiple `now`/`mtime` call sites → Mitigation: single `timestamps` module (step 1)

## Pre-Mortem

- **Plan fails because we only fix the UI and leave local `source_mtime`**: Cursor would look fine until COALESCE prefers a future Claude path; mixed clocks remain in SQL windows → Plan already requires ingest UTC + watermark reset, not UI-only
- **Plan fails because we change mtime to UTC without clearing watermarks**: UTC+ operators silently miss incremental updates → Already covered by Challenge “Watermark skew”
- **Plan fails by migrating column types to timestamptz / rewriting all rows in SQL**: Unnecessary risk and DuckDB/client complexity → Scope stays naive-UTC + wire `Z` + client parse; no timestamptz migration
- **Plan fails by treating peak_hour local display as in-scope and redesigning wrapped metrics**: Scope creep past issue #32 → Explicitly out of scope except documentation

## Preflight Amendments

- Use existing `metrics._iso` as the UTC wire chokepoint; update tests that assert no-`Z` ISO strings
- `0005` is DML-only (watermark clear); schema golden stays aligned with `0004`
- Claude message `ts` already flows through `_parse_ts` — step 3 covers message timestamps too

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Pre-Mortem complete
- [x] Preflight
- [ ] Build
- [ ] QA
