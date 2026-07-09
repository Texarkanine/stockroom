# Active Context

## Current Task: p4-dashboard / m2 — Vendored single-pane front-end (QA rework)

**Phase:** BUILD - COMPLETE (PASS)

## What Was Done

- Added overview `prev_distinct_projects` (Python metrics + empty/populated/shared/filtered contracts).
- Switched Projects KPI delta to `prev_distinct_projects`; anti-regression for summed `prev_projects`.
- Added pure `summarizeChartPanel` and wired `renderChart` to set `aria-label` + canvas fallback from it.
- Documented the additive overview field in `techContext.md`.
- Browser smoke: Projects `14` / `+27%` (14 vs 11); all seven canvases expose measured Aggregate/Compare summaries.
- Gate: 32 Node tests; 409 pytest passes / 3 skips; Ruff/format/lock/REUSE green; Torch 2.13.0+cu126 restored; encoder smoke 384-dim OK.

## Next Step

- Run `/niko-qa` for the post-rework semantic review.
