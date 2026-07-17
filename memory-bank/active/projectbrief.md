# Project Brief

## User Story

As a stockroom user, I want a dashboard view of who (user or agent) used which skills on which harness within my selected time window, so that I can understand meaningful skill-usage patterns and compare harnesses.

## Use-Case(s)

### Use-Case 1: Aggregate skill usage

Within the dashboard time window and selected harnesses, see counts of skills used, split by invoker (user vs agent), summed across harnesses.

### Use-Case 2: Compare skill usage across harnesses

In compare mode, see the same skill/invoker breakdown with harness as a visual grouping dimension.

### Use-Case 3: Choose a chart before final placement

Evaluate several mockup chart treatments (same 1×1 grid size as Tool Usage) on real warehouse data, then pick one for final layout placement next to Tool Usage.

## Requirements

1. Add a dashboard API endpoint that serves data for “who used which skill where” in the selected time range (and harness filter), with invoker (user/agent) and harness dimensions.
2. Count every discrete skill use: a session with 10 user uses and 5 agent uses of skill X counts as 10 + 5 (not deduped).
3. Extract skill usage via harness-specific functions (Claude, Cursor now; extensible for future harnesses) — not a single monolithic SQL query that embeds all harness rules.
4. Balance SQL (DuckDB-friendly filter/join/window) with Python post-processing (harness-specific parsing and aggregation).
5. Ground Claude extraction in real patterns: user-invoked skill at session front; later agent `Skill` tool use (including synthetic skill-info blobs).
6. Ground Cursor extraction in real patterns: agent `Read` of `…/SKILL.md` paths (and any manual skill patterns found).
7. Ship multiple Chart.js mockups in the main dashboard (same size as the Tool Usage panel), each supporting aggregate and compare modes.
8. After chart selection (follow-up), place the chosen chart next to Tool Usage and adjust layout (read/write ratio full row; session efficiency and prompt quality sharing a row) per [#63](https://github.com/Texarkanine/stockroom/issues/63).

## Constraints

1. Offline, read-only dashboard (`open_current()`); no schema migration unless extraction truly cannot work from existing `tool_calls` / `messages`.
2. Follow existing dashboard metrics patterns (`ENDPOINTS` registry, harness-keyed series, client-side aggregate/compare).
3. TDD for all code changes.
4. Mockup phase places candidates in the main dashboard at Tool Usage 1×1 size; final placement waits for operator pick.

## Acceptance Criteria

1. Endpoint returns skill-usage data sufficient for aggregate and compare charts (skill, invoker, harness, counts) over `since`/`until`/`harness` filters.
2. Per-harness extractor functions exist and are registered in an extensible pattern.
3. Claude and Cursor extractors correctly count real warehouse examples (including user vs agent invoker).
4. Several mockup panels render in the dashboard at Tool Usage size, each working in aggregate and compare mode against live API data.
5. Tests cover metrics endpoint behavior and extractor logic; dashboard static/JS tests updated as needed.
6. Operator can visually compare mockups and choose one for the follow-up placement pass.

## Rework

Operator feedback after the mockup ship (rework, not archive). Original brief above still applies; this section is additive.

### Rework User Story

As a stockroom operator, I want the nested skill chart to read as a sunburst (invoker groups with skills nested under each), clear top-N labeling on Tool/Skill Distribution panels, and tooltip colors that match the legend, so I can trust the mockups when picking a final chart.

### Rework Requirements

1. Rebuild the nested skill mockup as a **sunburst**: inner ring = user vs agent groups; outer ring = skills **within** each group; the user/agent boundary aligns across both rings; a skill used by both invokers appears as two outer segments.
2. **Agent-led colors**: assign palette from the agent side (group color + skills ranked by agent count; user-only skills take the next free slot); user side uses faded twins of those colors (same pattern as stacked compare bars).
3. Fix stacked skill-chart tooltip swatches so they match legend/bar fills (not inverted/mismatched).
4. Rename for parallel wording: **Tool Distribution (top N)** and **Skill Distribution … (mockup)** panels — both use “Distribution”; skill titles make top-N ranking obvious (same limit semantics as tools).
5. Keep post-reflect extraction fixes already in tree (Cursor `manually_attached_skills`, Claude built-in denylist, doughnut nearest hover).

### Rework Acceptance Criteria

1. Nested aggregate chart: no invoker split cutting through a skill segment; outer segments under user sum to the user inner arc (same for agent).
2. Same skill can appear on both user and agent outer arcs with paired solid/faded colors.
3. Compare-mode stacked tooltips use the same fill colors as the bars/legend.
4. Tool Distribution title includes `(top N)`; skill mockup titles use Skill Distribution + top-N clarity + `(mockup)`.
5. Existing extractor/metrics tests remain green; new/updated JS panel tests cover sunburst alignment and tooltip color helper if extracted.
