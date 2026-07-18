# Task: dashboard-model-analytics-pr70-rework

* Task ID: dashboard-model-analytics-pr70-rework
* Complexity: Level 2
* Type: bug fix / polish

Address two selected PR #70 items: (1) bucket `model_trends` by message `ts` when present else session activity; (2) make First-Prompt `.panel-range` time-range-only for all presets (explanatory copy stays in panel help/tooltip).

## Test Plan (TDD)

### Behaviors to Verify

- **Message ts buckets separately**: Claude session with one activity day, two attributed assistant turns with `messages.ts` on different calendar days → those turns land in different day buckets (not collapsed onto session activity).
- **Null ts falls back to session activity**: Cursor-style attributed turn with `messages.ts IS NULL` → still buckets at session activity (existing composer counts unchanged).
- **Ranking totals unchanged**: Same window fixtures as today → `model_trends` model order / total turn counts still match `models()["by_message"]` (only *which* bucket can move).
- **Default firstPrompt range is time-only**: `panelRangeLabels("default").firstPrompt` → `"Last 30 days"` (no “Average session length…” prefix).
- **Custom preset firstPrompt is time-only**: `panelRangeLabels("7d"|"30d"|"90d"|"1y").firstPrompt` → the bare window label (same string as `efficiency` / `models` for that preset).
- **HTML seed matches**: `#first-prompt-panel .panel-range` seed text is `"Last 30 days"`.
- **Help still explains the chart**: `PANEL_HELP["first-prompt"]` still describes average session length / prompt-detail bucketing (no regression of tooltip meaning).

### Edge Cases

- Session in window, message `ts` outside axis labels → skip that turn’s bucket increment if `_activity_bucket` label is absent (same as today’s missing-bucket skip).
- User turns / multi-model Cursor nulls → still no attribution (existing tests).
- `MessageRow` without `ts` in unit fixtures → `None` default; attribution unit tests keep passing.

### Test Infrastructure

- Framework: pytest (+ xdist) under `skills/sr-search/tests/`; Node 22 `--test` under `skills/sr-search/tests-js/`
- Conventions: `test_<behavior>` in `test_dashboard_metrics.py` / `test_dashboard_model_usage.py`; JS `node:test` in `dashboard-core.test.mjs`; static pins in `test_dashboard_static.py` if HTML seed is asserted
- New test files: none

## Implementation Plan

1. **Carry message timestamp through attribution**
   - Files: `tests/test_dashboard_model_usage.py`, `dashboard/model_usage.py`
   - Changes: Add optional `ts: datetime | None` to `MessageRow`; `attributed_turns` returns `(harness, session_id, model, ts)`; update unit assertions; `models()` unpacking ignores `ts`.

2. **Load `m.ts` and bucket trends by message time**
   - Files: `tests/test_dashboard_metrics.py`, `dashboard/metrics.py`
   - Changes: Tests first — multi-day `ts` split + null-`ts` fallback. Then SELECT `m.ts` into `MessageRow`; `model_trends` uses `message_ts or session_activity`; docstring matches creative (message-time-first).

3. **First-Prompt range labels are time-only**
   - Files: `tests-js/dashboard-core.test.mjs`, `dashboard-core.mjs`, `index.html` (+ static pin if present)
   - Changes: Tests for default + custom `firstPrompt` / assert no explanatory prefix. Set non-default `firstPrompt` to `windowLabel`; HTML seed → `Last 30 days`. If `PANEL_HELP["first-prompt"]` lacks the displaced meaning, add one short clause (it already covers averages by prompt bucket — verify only).

4. **Verify**
   - Files: none (run)
   - Changes: `make test-dashboard-py`, `make test-dashboard-js`, then full `make test`.

## Technology Validation

No new technology - validation not required

## Dependencies

- Existing creative contract: `creative-dual-grain-attribution.md` (message series bucket by `ts` else session activity)
- Schema: `messages.ts` (Claude populated; Cursor NULL)
- Existing `PANEL_HELP["first-prompt"]` for explanatory copy

## Challenges & Mitigations

- **Signature churn on `attributed_turns`**: Update `models()` + unit tests in the same TDD cycle as the NamedTuple change so nothing half-migrates.
- **Window vs bucket mismatch**: Keep window filter on session activity; only bucketing uses message `ts` — document in docstring so we don’t accidentally refilter the SQL join by `m.ts`.
- **Explanatory copy orphaned**: Operator wants it out of `.panel-range`; confirm help popover already carries the meaning before inventing new UI chrome.

## Pre-Mortem

- **Plan failed because we “fixed” labels by restoring the old explanatory corner text**: Operator override is explicit — time-only range; help owns meaning. Already covered by Challenge 3 / step 3.
- **Plan failed by bucketing on `ts` and also changing window membership**: Keep session-activity windowing; only the bucket key changes.
- **Plan failed by treating Cursor null `ts` as a bug**: Fallback is required honesty; covered by null-ts behavior + existing composer fixtures.

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Pre-Mortem complete
- [ ] Preflight
- [ ] Build
- [ ] QA
