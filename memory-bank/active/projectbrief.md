# Project Brief

## User Story

As a dashboard user, I want horizontal bar chart hover tooltips to match the bar under my cursor so that Model Distribution (and other horizontal charts) are readable without guessing.

## Use-Case(s)

### Use-Case 1

Hover a horizontal bar (e.g. a model name in Model Distribution): the highlighted bar and tooltip title/value both refer to that same category, and the tooltip stays stable as the pointer moves within that row.

### Use-Case 2

Hover a vertical bar chart (Daily Activity, Session Efficiency, First-Prompt Quality): behavior remains correct — no regression from fixing horizontal interaction.

## Requirements

1. Fix Chart.js hover/tooltip interaction on horizontal bar panels (`indexAxis: "y"`) so index selection uses the Y axis.
2. Keep hover highlighting and tooltip content aligned (same interaction settings for both).
3. Leave vertical charts and non-bar charts working as today.
4. Cover the behavior with dashboard JS tests (TDD).

## Constraints

1. Stay within the existing dashboard static front-end (vendored Chart.js; no new bundler/CDN).
2. No product/API/metrics changes unless required for the fix.
3. Follow project TDD and test-running practices.

## Acceptance Criteria

1. On Model Distribution / Sessions by Project / Tools-in-compare, hovering a bar shows a tooltip for that same category.
2. Vertical bar charts still show correct tooltips on hover.
3. Dashboard JS tests pass (`make test-dashboard-js` or equivalent).
