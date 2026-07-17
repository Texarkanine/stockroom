---
task_id: dashboard-skill-usage
date: 2026-07-17
complexity_level: 3
---

# Reflection: dashboard-skill-usage

## Summary

Shipped harness-extensible skill-usage extraction, `/api/skills`, and three Set A Chart.js mockups in the main dashboard so the operator can pick a visual before final placement. Build and QA both passed; creative decisions held.

## Requirements vs Outcome

All project-brief acceptance criteria for this mockup phase were met: endpoint with skill/invoker/harness counts, Claude + Cursor extractors in a registry, discrete counting (no session dedupe), three Aggregate/Compare mockups at Tool Usage size with `(mockup)` titles. Final layout placement next to Tool Usage remains an explicit follow-up after the operator picks a chart — correctly out of scope.

## Plan Accuracy

The amended post-preflight plan matched reality: extractors → metrics → client ENDPOINTS → panel builders → static markup. Preflight’s addition of `dashboard-data.test.mjs` and `test_dashboard_static.py` inventory pins was load-bearing — those would have been easy to miss. Ranking expectation in the mix test needed one correction (niko totals 2 across harnesses/invokers), which the plan’s tie-break rules already implied. Nested-doughnut Chart.js geometry stayed a soft risk; compare-mode degradation to stacked bars avoided a plugin rabbit hole.

## Creative Phase Review

- **Extractor architecture (Option B)**: Held cleanly. Candidate SQL + `EXTRACTORS` registry + server aggregate matched ingest/workspace_key extensibility and kept panels presentation-only.
- **Mockup Set A**: Held. Nested aggregate with dual doughnut datasets is imperfect vs true dual-ring geometry; compare stacking by `{harness} · {invoker}` with invoker alpha is the honest four-stack encoding the creative called for. Titles and one-line encoding blurbs made the temporary gallery self-explanatory.

## Build & QA Observations

Build was mostly linear TDD. Friction points: (1) DuckDB `json_extract_string` on stored JSON strings worked without casts; (2) nested doughnut label-length mismatch is visual mockup debt, not an API issue. QA found only a KISS cleanup (`skills()` iterate `names`). No rework loop.

## Cross-Phase Analysis

Preflight → Build was the highest-value link: inventory-pin tests and real-shaped fixtures prevented incomplete wiring. Creative’s explicit “no mondo SQL” and “skill blobs ignore” rules prevented the two failure modes called out in the pre-mortem. No creative decision created a QA FAIL.

## Insights

### Technical
- Dashboard endpoint/panel inventories are already regression-pinned in JS and static tests — treat those lists as part of the public contract of any new `/api/*` + panel work.
- When ranking multi-dimensional series (skill × harness × invoker), write the expected totals before asserting order; cross-harness sums are easy to mis-sketch in tests.

### Process
- Preflight amendments that force “tests then wire” on inventory-pin files pay for themselves immediately on Level 3 dashboard work.
- Nothing notable on workflow overhead for this task — creative → plan → preflight → build → QA fit the scope.
