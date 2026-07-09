---
task_id: p4-dashboard-m2
date: 2026-07-09
complexity_level: 3
---

# Reflection: Vendored single-pane front-end

## Summary

Milestone m2 delivered the fully offline single-pane dashboard front-end, then closed a QA-driven rework that made the Projects KPI delta distinct-to-distinct and gave every chart canvas a content-bearing accessible summary. The final gate and semantic review both passed.

## Requirements vs Outcome

Every original m2 requirement shipped: open harness discovery, positional colors, client-owned Aggregate/Compare, mode-independent KPIs, seven chart panels, recent sessions, eight factual wrapped cells, atomic same-origin refresh, actionable warehouse refusals, responsive light/dark presentation, vendored Chart.js 4.5.1, precise REUSE ownership, Node 22 contracts, and no package manager or build path.

The QA rework added one intentional public-boundary amendment: overview `prev_distinct_projects`. That completed the Projects delta contract rather than expanding product scope. Chart summaries implemented the already-settled interaction-contract accessibility requirement; they were incomplete in the first build, not a new feature ask.

## Plan Accuracy

The original preflight-amended ten-step plan was accurate for the front-end surface, REUSE ownership, Node testing boundary, and browser-only checks. The first build followed it closely and passed mechanical CI.

The plan's weak seam was the Projects previous-window contract. It treated `distinct_projects` versus summed `prev_projects` as acceptable client math under a "no JSON shape changes" boundary. That assumption survived preflight and the first build, then failed semantic QA. The rework plan that followed was accurate: five TDD steps, shared-project fixtures on both sides, pure summary generation, and adapter-only application.

## Creative Phase Review

The contract-first native interaction decision held, including the accessibility note that canvas labels must carry measured content. The first build under-implemented that note with title/mode-only `aria-label`s; the rework restored the creative intent without redesign.

The native-ESM/Node-testing decision also held and paid off again during rework: Projects delta and chart summaries were fixed entirely in tested pure modules before the adapter touched the DOM.

The Projects previous-window creative, added after the first QA FAIL, held cleanly in build: the server already had previous project sets, so an additive union field was the smallest correct fix.

## Build & QA Observations

The first build's staged TDD and browser pass were strong for packaging, races, theme redraw, and offline behavior. Formal QA then correctly failed on two substantive blockers rather than rubber-stamping a green suite.

The rework build was uneventful because the plan named the exact failing assertions to rewrite, including the Node `+100%` case that encoded the buggy baseline. Live-warehouse smoke confirmed Projects `+27%` (14 vs 11) and measured Aggregate/Compare canvas summaries. The second QA was clean.

## Cross-Phase Analysis

The first QA FAIL was a planning/creative gap, not a coding miss: distinct current values cannot truthfully delta against summable previous counts, and title/mode labels do not satisfy a measured-content accessibility contract. Preflight of the original plan could not catch the missing previous distinct field because the plan itself treated the false comparison as in-bounds.

The rework loop worked as designed: FAIL → plan/creative → preflight amendment → build → clean QA. Keeping summary prose out of the adapter made the second QA a completeness check rather than a second design debate.

## Insights

### Technical

- Non-summable KPI cards need an explicit previous-window rollup of the same grain before any client delta is planned; per-harness previous counts are not a substitute for a filtered distinct union.
- Canvas accessibility is a content contract, not an attribute-presence check: summaries must include measured values or an explicit no-data sentence, and that prose belongs in pure tested code.

### Process

- A green first CI gate does not prove semantic KPI honesty. Challenge distinct-versus-summable comparisons and accessibility content before calling a dashboard milestone done.
- When QA fails on a missing contract, amend the public boundary narrowly rather than hiding the trend or redefining the metric to make the old math work.
