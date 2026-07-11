# Task: Session Inspection in Dashboard (#39)

* Task ID: session-inspection-dashboard
* Complexity: Level 3
* Type: feature

Add a dashboard conversation-reconstruction view reachable from Recent Sessions and by deep-linkable session URL, with basic vendored markdown rendering and optional markdown/JSON export — per [#39](https://github.com/Texarkanine/stockroom/issues/39).

## Component Analysis

### Affected Components
- **`stockroom.dashboard.metrics`**: Mode-agnostic SQL metrics for the dashboard API → add session-detail reconstruction query; extend `sessions()` wire payload with identifiers needed for navigation
- **`stockroom.dashboard.server`**: Loopback HTTP + static serving → register new API endpoint; possibly adjust static routing if path-based deep links are chosen
- **Dashboard static front-end** (`static/index.html`, `dashboard.mjs`, `dashboard-data.mjs`, `dashboard-core.mjs`): Single-pane metrics UI with no routing → add session view, navigation from Recent Sessions, deep-link handling, markdown render, optional export
- **Vendored front-end deps** (`static/chart-4.5.1.umd.min.js` + `REUSE.toml`): Offline Chart.js pattern → vendor a basic markdown JS library the same way
- **Skills (`sr-dashboard`, possibly `sr-search`/`sr-query`)**: Today only print root URL / CLI full-text → document deep-link URL template so skills can offer session inspection links
- **Licensing tests** (`tests/test_licensing.py`): Chart.js MIT pin → mirror for markdown artifact

### Cross-Module Dependencies
- Front-end → server `/api/*` → `metrics.*` → `warehouse.open_current()` (read-only)
- Session list click / deep link → session-detail API → render markdown in browser
- Export downloads from already-fetched reconstruction payload (client-side; no new write path)
- Skills → documented URL template → operator browser (no engine call required for viewing)

### Boundary Changes
- **API**: New reconstruction endpoint returning full message text (and likely tool calls); `sessions()` gains `session_id` (and already has `harness`) for click-through
- **Front-end**: First drill-down / multi-view surface (P4 was explicitly single-pane)
- **No schema migration** — reconstruction uses existing `messages` / `tool_calls` ordering contracts
- **REUSE.toml**: New MIT (or upstream) override for vendored markdown artifact

### Invariants & Constraints
- Must preserve read-only dashboard path (`open_current()`, no migrate/ingest)
- Must remain fully offline at runtime (no CDN)
- Must preserve composite session identity `(harness, session_id)`
- Must return exact warehouse text for reconstruction (no `truncate_cell` on detail path)
- Must render **basic markdown only** — no Mermaid, footnotes, or other extensions
- Must not introduce a front-end package manager / bundler unless creative explicitly chooses otherwise
- Non-goal: replacing CLI `--detail raw` / `sr-query` as the programmatic full-text surface

## Open Questions

- [x] **Deep-link URL & client navigation** → Resolved: query params on `/` — `?view=session&harness=&session=` (see `memory-bank/active/creative/creative-deep-link-navigation.md`)
- [ ] **Markdown library & HTML safety** — Which JS library to vendor, in what module shape (UMD/ESM), and whether to sanitize HTML before DOM insert? Ambiguous because several small libraries fit "basic markdown," Chart.js set a UMD precedent, and markdown→HTML has XSS implications even on loopback. Constraints: offline vendor; basic markdown only (no extension ecosystem); REUSE-annotatable; no npm/bundler at runtime.
- [ ] **Reconstruction content model** — What does the conversation view include (messages only vs messages + tool_calls; subagent sessions; export formats)? Ambiguous because "reconstruct a conversation" can mean chat turns only or the full agent turn including tools, and export is optional in the issue. Constraints: ordered by existing schema contracts; useful for skill deep-links; export is markdown and/or JSON if included.

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
