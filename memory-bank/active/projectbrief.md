# Project Brief

## User Story

As a stockroom dashboard user, I want to see which models get my attention — both as ranked totals (by conversation and by message) and as a stacked area over time — so I can tell marathon-model use apart from high-frequency everyday models.

## Use-Case(s)

### Use-Case 1: Ranked model attention

Open the dashboard and compare top models by conversation count vs by message count (addresses [#67](https://github.com/Texarkanine/stockroom/issues/67)).

### Use-Case 2: Model mix over time

Open the dashboard and see a stacked area time-series of model usage so color/area shows which models dominate in each period (addresses [#68](https://github.com/Texarkanine/stockroom/issues/68)).

## Requirements

1. Deliver both [#67](https://github.com/Texarkanine/stockroom/issues/67) and [#68](https://github.com/Texarkanine/stockroom/issues/68) in one effort.
2. Extend top-models beyond conversation-only grain to include message-grain ranking (chart layout TBD in creative).
3. Add a stacked area chart of model usage over time (Y = conversations and/or messages — TBD in creative; likely full/2-column width).
4. Stay within the existing offline read-only dashboard stack (`metrics.py`, `/api/*`, Chart.js panels).
5. Handle harness honesty for model attribution (Claude has per-message `messages.model`; Cursor often does not).

## Constraints

1. Offline, read-only warehouse access via existing dashboard patterns.
2. No inventing message-level model data where the warehouse has NULLs — document or define fallback rules explicitly.
3. TDD for metrics/API and client panel builders.
4. Prefer shared grain/attribution helpers over duplicated SQL for conversation vs message.

## Acceptance Criteria

1. Dashboard shows conversation-grain and message-grain top-models information (resolved layout from creative).
2. Dashboard shows a stacked area of model usage over time at an appropriate width (resolved grain/layout from creative).
3. Metrics/API and static panel inventory are covered by tests; full suite passes.
4. Issues #67 and #68 are addressed by the shipped behavior (ready to close when verified).

## Rework

PR #70 CodeRabbit feedback (operator-selected items only):

1. **Message-time bucketing for `model_trends`**: Attribute assistant turns as today; bucket each turn by `messages.ts` when present, else session activity; cover multi-day turns in separate date buckets.
2. **First-Prompt range label is time-only**: For every date-range preset, `#first-prompt-panel .panel-range` shows only the window (“Last 30 days”, etc.). Remove “Average session length by prompt detail · …” from that corner text; if that explanation is still needed, it belongs in the panel tooltip/help, not the range line.
