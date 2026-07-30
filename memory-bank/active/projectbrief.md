# Project Brief

## User Story

As a stockroom dashboard user, I want to see per-conversation skill and tool-call distribution as pie charts on the conversation overview, so that I can quickly grasp how a session spent its agentic effort — and I want a matching advanced query recipe so the same insight is available outside the UI.

## Use-Case(s)

### Use-Case 1

Open a conversation overview on the dashboard and see skill and tool-call distribution visualized (pie charts or a stronger pattern if prior art suggests one).

### Use-Case 2

Consult advanced query recipes and run an equivalent SQL/recipe that surfaces the same per-conversation skill/tool distribution.

### Use-Case 3

Before layout is locked, review mockups of candidate placements (side column, inline, popover, plus any better internet-sourced pattern) and pick one via visual UAT.

## Requirements

1. Visualize skill-call distribution per conversation on the dashboard conversation overview.
2. Visualize tool-call distribution per conversation on the same overview.
3. Include an advanced query recipe covering this insight.
4. Before locking placement: brief internet prior-art scan for conversation/session analytics visualization patterns; produce mockups of the issue's three candidates (side / inline / popover) and any stronger alternative found; operator picks visually.
5. Closes [issue #107](https://github.com/Texarkanine/stockroom/issues/107).

## Constraints

1. Fit the existing dashboard conversation overview UI and visual language; do not invent a parallel design system.
2. Layout choice is deferred until after mockups + operator pick (creative phase).
3. Prefer reusing existing warehouse/API data over new ingestion pipelines.

## Acceptance Criteria

1. On a conversation overview with tool/skill activity, distribution pie charts (or the chosen visualization) are visible in the operator-selected placement.
2. Empty / sparse sessions degrade gracefully (no broken charts).
3. An advanced query recipe documents how to obtain the same distribution via the query surface.
4. Operator has visually selected layout from mockups before build proceeds on placement.

## Rework

### Trigger

Operator UAT on a real session (`8512de74-…`) showed empty Tools/Skills composition boxes despite nested tool calls in the transcript. Initially framed as a bad aggregation query (prefer harness-scoped / visitor-style session metrics). Operator later confirmed the dashboard process had not been bounced after the feature land — stale modules, not a wrong query. Fresh `session_detail` already returns correct tools/skills for that session.

### Remaining requirements

1. When a conversation has no tool calls and/or no skill uses, do **not** reserve full doughnut chart height for empty panels. Still surface a compact “none found” signal so emptiness is distinguishable from a load/render failure.
2. Bounce / `--replace` the local dashboard after verifying so live UAT matches current code.
3. Session composition doughnuts should be denser than metrics-pane defaults (shorter height, side legend) so the transcript starts higher.
4. No shrink FOUC: wraps must not paint at metrics height then collapse/densify after the session fetch.

### Out of scope (unless re-requested)

Visitor / per-harness query-object rewrite for session composition — current implementation already loads one `(harness, session_id)` and aggregates in memory; warehouse-window multi-harness path stays on the main metrics dashboard only.
