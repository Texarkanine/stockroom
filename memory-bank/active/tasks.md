# Task: conversation-summary-tool-skill-pie-charts

* Task ID: conversation-summary-tool-skill-pie-charts
* Complexity: Level 3
* Type: feature

Per-conversation skill and tool-call distribution visualizations on the dashboard session overview (`?view=session`), plus an advanced query cookbook recipe. Layout deferred to creative (mockups + operator visual pick). Closes [#107](https://github.com/Texarkanine/stockroom/issues/107).

## Component Analysis

### Affected Components
- **Dashboard session UI** (`skills/sr-search/src/stockroom/dashboard/static/` — `index.html`, `dashboard.mjs`, `dashboard-session.mjs`, CSS in `index.html`): reconstructs chat in `#session-pane`; single `min(1200px)` column; no side rail today. Needs distribution viz placement + Chart.js wiring (vendored Chart.js already used on metrics pane).
- **Dashboard metrics chart helpers** (`dashboard-core.mjs` — `buildToolsPanel`, `buildSkillsNestedPanel`, `renderChart` in `dashboard.mjs`): existing doughnut / nested-doughnut patterns to reuse or adapt for session scope.
- **Session detail API** (`server.py` `_serve_session` → `metrics.session_detail`): returns nested `messages[].tool_calls` but no session-level tool/skill aggregates; skills absent from this payload today.
- **Skill usage derivation** (`skill_usage.iter_skill_uses` / `metrics.skills`): warehouse-window aggregates; must be scoped (or paralleled) per session for the overview.
- **Query cookbook** (`skills/sr-query/references/cookbook/` + `docs/advanced/cookbook/` symlinks): tools/skills recipes exist globally; none per-session distribution — add recipe + index link.

### Cross-Module Dependencies
- Session UI → `GET /api/session` → `metrics.session_detail` → DuckDB `sessions` / `messages` / `tool_calls` (+ skill derivation).
- Cookbook recipes are independent read-path docs over the same warehouse tables (no dashboard dependency).

### Boundary Changes
- Likely extend `session_detail` JSON (or a sibling session summary field) with tool/skill distribution counts — public dashboard API contract change (local offline UI only; still treat as intentional wire shape).
- New cookbook recipe file + index row (docs/skill references).

### Invariants & Constraints
- Must preserve offline, no-CDN dashboard (vendored Chart.js only).
- Must preserve existing session deep links (`?view=session&harness=&session=` + `#msg-N`).
- Must not invent a new design system — match existing dashboard tokens/chrome.
- Skills are derived (no `skills` table); reuse harness-aware skill_usage patterns.
- Cookbook SSOT remains under `skills/sr-query/references/cookbook/`; docs symlink only.
- Layout placement must be chosen by operator after mockups (requirement).

## Open Questions

- [x] **Session overview distribution placement & presentation** → Resolved: **F** — overview pill (title → session 4 metrics → composition tools/skills charts, no prose) + messages-only card. See `memory-bank/active/creative/creative-session-distribution-placement.md`.

## Status

- [x] Component analysis started
- [ ] Open questions resolved
- [ ] Test planning complete (TDD)
- [ ] Implementation plan complete
- [ ] Technology validation complete
- [ ] Pre-Mortem complete
- [ ] Preflight
- [ ] Build
- [ ] QA
