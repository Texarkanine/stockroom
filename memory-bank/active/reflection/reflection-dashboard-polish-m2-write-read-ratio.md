---
task_id: dashboard-polish-m2-write-read-ratio
date: 2026-07-10
complexity_level: 2
---

# Reflection: dashboard-polish-m2-write-read-ratio

## Summary

Rewrote the Write/Read panel to plot write-share ratio series (aggregate one line; compare per harness) with honest `null` gaps on zero-denominator weeks. Delivered to plan; `make ci` green.

## Requirements vs Outcome

Issue #6 acceptance met: ratio series, mode-aware dataset shape, null gaps, title/axis/legend/aria aligned, pure `buildWriteReadPanel` / `writeShare` tests. No descopes; absolute tooltip enrichment left deferred as planned.

## Plan Accuracy

Sequence and file list held. Anticipated `hasValues`/`finiteNumber` null-vs-zero footgun materialized and was handled via `ratioSeriesEmpty` + `empty` override. Only correction was a wrong hand-computed aggregate fixture (3/7 not 0.5).

## Build & QA Observations

TDD red→green was smooth; QA found nothing substantive. Adapter stayed three touchpoints (colors, title, `yMax`).

## Insights

### Technical
- When a panel needs a *paired* series (writes+reads → ratio), `selectedDatasets` cannot be reused — a dedicated builder path is the right seam, not a forced generalization.

### Process
- Nothing notable

### Million-Dollar Question

If ratio had been the original chart model, weekly trends would still ship absolute counts as substrate and the client would own `writeShare` + mode branching — same shape we landed on. Nothing more elegant was left on the table.
