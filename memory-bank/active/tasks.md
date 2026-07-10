# Task: dashboard-polish-m2-write-read-ratio

* Task ID: dashboard-polish-m2-write-read-ratio
* Complexity: Level 2
* Type: simple enhancement

Change the Write/Read panel so it plots a true write-share ratio series (`writes / (writes + reads)`) in Aggregate (one blended line) and Compare (one line per selected harness), with honest `null` gaps for zero-denominator weeks — not absolute write/read volume dual-series. Server `/api/trends` weekly absolute counts stay as substrate; no Python metrics change.

## Test Plan (TDD)

### Behaviors to Verify

- Aggregate ratio: weekly payload with selected harnesses → exactly one line dataset whose points are blended `sum(writes) / (sum(writes)+sum(reads))` per week.
- Compare ratio: same payload → one line per selected harness (positional colors), each point `writes[h] / (writes[h]+reads[h])`.
- Zero denominator: week where writes+reads === 0 (aggregate or per harness) → `null` at that index (gap), never a fake `0` ratio.
- Meaningful zero ratio: writes=0 and reads>0 → `0` (not null); panel is not marked empty solely because ratios are zero.
- Empty panel: all weeks null / no activity → `empty: true`; any finite ratio (including 0) → `empty: false`.
- Presentation: line chart, not stacked; aggregate legend label reflects ratio (not "Writes"/"Reads"); compare legends use display harness names.
- Aria/title: render path uses ratio-oriented chart title; `summarizeChartPanel` shows `—` (or equivalent) for `null` points instead of coercing them to `0`.
- Static shell: `#write-read-chart` default aria/text no longer claims absolute "write and read tool calls" quantities.
- Regression: other panel builders and existing dashboard-core/data/static contracts stay green; Python trends API unchanged.

### Edge Cases

- Missing/partial harness series → treat missing as 0 counts for that harness (existing `seriesFor` / `finiteNumber` behavior) before ratio.
- Single harness selected in compare → one ratio line.
- Empty weeks array → empty panel.
- Mode ignored today → after change, aggregate vs compare must diverge on dataset count/shape.

### Test Infrastructure

- Framework: Node 22 `node:test` (`make test-js`); pytest for static HTML (`uv run --no-sync pytest`).
- Test location: `skills/sr-search/tests-js/`, `skills/sr-search/tests/`.
- Conventions: `test("…")` in `dashboard-*.test.mjs`; `test_*` in `test_dashboard_*.py`.
- New test files: none (extend `dashboard-core.test.mjs`, `test_dashboard_static.py` as needed).

## Implementation Plan

1. [x] **Ratio math + panel model (TDD)** — write failing tests first for a pure `writeShare(writes, reads) → number|null` (0/0 → `null`; writes=0 & reads>0 → `0`) and for `buildWriteReadPanel` aggregate (one ratio line) / compare (one line per harness, positional colors) / empty vs all-zero-ratio; then implement helper + rewrite `buildWriteReadPanel(payload, selected, mode, colors)`. Replace obsolete dual absolute-series test. Use `panelModel` optional `empty` override (or equivalent) so finite `0` ratios are not treated as empty.
   - Files: `tests-js/dashboard-core.test.mjs`, `static/dashboard-core.mjs`
   - Changes: export `writeShare`; ratio series only; signature gains `colors`.

2. [x] **Honest nulls in aria summaries (TDD)** — write/adjust failing tests (`summarizes dual-series…` → ratio title + null-point case) first; then change `summarizeChartPanel` so `null`/non-finite points render as `—` (numeric `0` still `0`).
   - Files: `tests-js/dashboard-core.test.mjs`, `static/dashboard-core.mjs`
   - Changes: display path only; other summary tests remain valid for numeric data.

3. [x] **Static contract (TDD) then adapter glue** — write failing `#write-read-chart` aria/text assertions in `test_dashboard_static.py` first; update `index.html` fallback copy to ratio semantics; after steps 1–2 green, wire `dashboard.mjs` only: pass `colors`, ratio-oriented `renderChart` title, and `chartOptions` respect for model `yMax: 1` (0–1 scale). No new business logic in the adapter — if Y-scale policy needs tests, put the flag on the panel model in core (covered by step 1) and only read it in `chartOptions`.
   - Files: `tests/test_dashboard_static.py`, `static/index.html`, `static/dashboard.mjs`
   - Changes: presentation only; no request-plan / server changes.

4. [x] **Verification** — `make test-js`, targeted dashboard pytest, then `make ci` at milestone boundary.

### Preflight amendments (2026-07-10)

- Made `writeShare` a required exported pure helper with tests (not optional).
- Spelled out test-before-code on every implementable unit; step 3 splits static TDD from adapter glue.

## Technology Validation

No new technology - validation not required (native ES modules + existing Chart.js).

## Dependencies

- Existing weekly trends payload shape (`weeks`, `writes`, `reads` harness-keyed arrays) from `/api/trends`.
- Existing harness color / `displayHarness` / `orderedSelection` helpers.
- m1 date-range wiring already supplies windowed weekly trends when a preset is active — out of scope to change.

## Challenges & Mitigations

- **`hasValues` treats `null` as 0 via `finiteNumber`:** Ratio panels with only gaps would look empty (good), but all-zero *ratios* (writes=0, reads>0) would also look empty (bad). Mitigation: override `empty` for write-read based on presence of any finite ratio, or teach empty-detection to distinguish `null` from `0` without changing count-panel “all zeros → empty” UX.
- **`summarizeChartPanel` coerces null → 0:** Misleading aria for gap weeks. Mitigation: step 2 — display `—` for null/non-finite.
- **Y-axis scale:** Counts use unbounded Y; ratio needs 0–1. Mitigation: optional `yMax` (or equivalent) on the panel model consumed by `chartOptions`.
- **Compare without colors arg:** Today `buildWriteReadPanel` ignores mode and colors. Mitigation: add `colors` parameter and wire from adapter like other panels.

## Pre-Mortem

- **Plan failed by leaving absolute dual series and only renaming the title:** Acceptance requires dataset shape change; step 1 tests lock single aggregate line / per-harness compare lines and forbid Writes+Reads absolute datasets.
- **Plan failed by plotting fake 0 on idle weeks, looking like “0% writes”:** Already covered by Challenge on null gaps + explicit zero-denominator tests.
- **Plan failed by changing Python metrics to precompute ratios:** Unnecessary; client owns presentation. Keep server absolute counts — already in scope statement.
- **Plan failed by breaking empty-state for other charts while fixing ratio empty detection:** Mitigation: do not globally redefine `hasValues` for count panels; scope empty override to write-read (or null-aware check only where nulls are intentional).

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Pre-Mortem complete
- [x] Preflight
- [x] Build
- [ ] QA
