---
task_id: dashboard-skill-sunburst-rework
date: 2026-07-17
complexity_level: 2
---

# Reflection: dashboard-skill-sunburst-rework

## Summary

Reworked the nested skill mockup into an aligned sunburst with agent-led skill colors, fixed stacked tooltip swatches, and renamed Tool/Skill panels to Distribution `(top 10)`. Post-reflect operator polish selected the sunburst (dropped stacked/tools-like mockups and mockup title cues), split categorical `PALETTE` from `AGGREGATE_COLOR`, added black doughnut `RING_BORDER`, and tightened lower-panel layout.

## Requirements vs Outcome

Planned rework criteria landed in build/QA: circumference-aligned outer/inner arcs, dual-invoker outer segments with paired solid/faded skill colors, compare-mode tooltip fill parity, Distribution `(top 10)` wording. No API changes.

Operator polish then went past the written rework plan: kept only the sunburst as `Skill Distribution (top 10)` (no `(mockup)` / `(sunburst)` title cues); removed stacked and tools-like panels; reordered Model Distribution before Session Efficiency and collapsed First-Prompt to one grid cell. Palette polish changed the sunburst invoker ring from `PALETTE[0]` to shared `AGGREGATE_COLOR` (accent indigo), with categorical hues on harness/tool/skill series only.

## Plan Accuracy

The four-step TDD sequence (sunburst → tooltip helper → titles → verify) matched the planned rework. Circumference-sum tests caught the alignment risk from the pre-mortem. Chart.js legend duplication stayed accepted mockup debt until the other mockups were removed.

Surprises were post-reflect visual: orange-first categorical `PALETTE` made aggregate/“All harnesses” charts look like a harness series until `AGGREGATE_COLOR` was split out; match-fill doughnut borders hid opaque agent wedges and a single `aggregateDataset` border hue painted every tools arc.

## Build & QA Observations

Planned build was straightforward once outer ordering and palette reservation were test-locked. QA only applied a trivial DRY cleanup (`skillColor`). Operator polish iterated on live visuals (palette B, aggregate accent, ring borders, layout) with JS/static tests updated alongside; no second formal QA loop.

## Insights

### Technical
- Chart.js tooltip swatches can prefer `borderColor` over `backgroundColor`; for faded-fill / solid-border stacked bars, set both `labelColor` fill and stroke to the fill so legend, bar, and tooltip agree.
- Once the first categorical slot is a harness hue, `PALETTE[0]` must not double as the aggregate/sum color — keep a separate `AGGREGATE_COLOR` (and use it for the sunburst invoker ring).
- Leaving `aggregateDataset`'s single border on a multi-fill doughnut strokes every arc and legend swatch with one hue; match-fill borders hide opaque wedges — prefer an explicit neutral `RING_BORDER`.

### Process
- Visual chart selection and layout tweaks naturally arrive after reflect; fold them into the reflection before archive rather than treating the first reflect doc as frozen.

### Million-Dollar Question

If the sunburst had been the chosen encoding from day one — with categorical vs aggregate colors and explicit ring borders as dashboard-wide rules — the three-mockup ship and the later nested→sunburst rework would collapse into one client reshape of `/api/skills`, one Skill Distribution panel beside tools, and no post-hoc aggregate-color regression. The compare stacked-bar path and extractor/API side would stay the same.
