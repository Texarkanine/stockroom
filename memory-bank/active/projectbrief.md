# Project Brief

## User Story

As a stockroom operator, I want the local dashboard's controls and charts polished for clarity and control so that I can select time windows, read modes and metrics correctly, and recognize projects at a glance without leaving the single pane.

## Use-Case(s)

### Select a date range for windowed metrics

Operator picks a range in the top controls bar; all windowed KPIs and charts refetch with `since`/`until`; panel labels and prior-period % deltas follow the selection. Wrapped stays all-time.

### Switch Aggregate / Compare at a glance

Operator sees one exclusive segmented control for Aggregate vs Compare and never mistakes the modes for independent buttons.

### Read Write/Read as a true ratio

Operator sees ratio series (aggregate: one blended line; compare: one line per harness), not absolute write/read volumes under a ratio title.

### Understand opaque efficiency metrics

Operator clicks an info icon on Session Efficiency and First-Prompt Quality to learn bucket thresholds and chart meaning.

### Recognize projects by friendly name

Operator sees leaf names (e.g. `stockroom`) when `cwd` is recoverable, with the unique `project_id` slug available on hover.

## Requirements

1. Implement [#4](https://github.com/Texarkanine/stockroom/issues/4) — date-range selector in the top controls bar (wire `since`/`until`, refresh labels, prior-window % deltas; Wrapped unfiltered).
2. Implement [#5](https://github.com/Texarkanine/stockroom/issues/5) — Aggregate/Compare as an obvious exclusive toggle (visual/ARIA only; no API/mode-semantics change).
3. Implement [#6](https://github.com/Texarkanine/stockroom/issues/6) — Write/Read plots ratio, not absolute quantities (aggregate + compare; honest zero-denominator handling).
4. Implement [#7](https://github.com/Texarkanine/stockroom/issues/7) — info-icon tooltips for Session Efficiency and First-Prompt Quality only.
5. Implement [#8](https://github.com/Texarkanine/stockroom/issues/8) — friendly project names by default; full `project_id` on hover; grouping remains by `project_id`.

## Constraints

1. Single L4 project covering issues #4–#8; deliver via milestones (operator-preferred cut recorded in active context).
2. Preserve p4 dashboard invariants: read-only warehouse path, fully offline (no CDN), mode-agnostic per-harness API, client-owned Aggregate/Compare, port 6767, no bundler.
3. `sessions.project_id` remains the grouping/identity key; never decode the slug for ranking.
4. Wrapped remains all-time and unfiltered by the date-range control.
5. Test-first; green `make ci` (incl. JS dashboard contracts) at each milestone boundary.

## Acceptance Criteria

1. Each of #4–#8 acceptance checklists is satisfied (see linked issues).
2. Milestone boundaries leave the dashboard shippable and offline-correct after every sub-run.
3. No regression to harness discovery, positional colors, or existing windowed endpoint contracts beyond intentional date-range wiring and project-label metadata.
