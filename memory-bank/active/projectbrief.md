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
