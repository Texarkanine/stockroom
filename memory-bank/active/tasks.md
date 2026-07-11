# Task: Session Inspection in Dashboard (#39)

* Task ID: session-inspection-dashboard
* Complexity: Level 3
* Type: feature

Add a dashboard conversation-reconstruction view reachable from Recent Sessions and by deep-linkable session URL, with basic vendored markdown rendering and markdown/JSON export — per [#39](https://github.com/Texarkanine/stockroom/issues/39).

## Pinned Info

### Session inspection flow

Pinned because navigation, API, and export all share one identity contract (`harness` + `session_id`) and one payload.

```mermaid
flowchart TD
  List["Recent Sessions row"] -->|"pushState view=session"| URL["/?view=session&harness&session"]
  Skill["Skill / pasted link"] --> URL
  URL --> Boot["dashboard.mjs boot"]
  Boot -->|metrics| PaneM["Metrics pane"]
  Boot -->|session view| Fetch["GET /api/session"]
  Fetch --> Metrics["metrics.session_detail"]
  Metrics --> WH[(DuckDB read-only)]
  Fetch --> PaneS["Session pane"]
  PaneS --> MD["markdown-it html:false"]
  PaneS --> Export["Download .md / .json"]
```

## Component Analysis

### Affected Components
- **`stockroom.dashboard.metrics`**: Mode-agnostic SQL metrics → add `session_detail()`; extend `sessions()` wire with `session_id`
- **`stockroom.dashboard.server`**: Loopback HTTP → register endpoint; parse required `harness` + `session` (special-case like `limit` on sessions)
- **Dashboard static front-end** (`index.html`, `dashboard.mjs`, `dashboard-data.mjs`, `dashboard-core.mjs`): Single-pane UI → session pane, query-param navigation, markdown render, export helpers
- **Vendored deps + `REUSE.toml`**: Chart.js pattern → vendor `markdown-it-14.1.0.min.js` with MIT override
- **Skills (`sr-dashboard`, light touch on search/query if they surface session ids)**: Document deep-link URL template
- **Licensing / static tests**: Mirror Chart.js offline + MIT assertions for markdown-it

### Cross-Module Dependencies
- Front-end → `/api/session` → `metrics.session_detail` → `warehouse.open_current()`
- List click / deep link share URL template from creative-deep-link-navigation
- Export is client-only from fetched JSON (no write path)

### Boundary Changes
- **API**: New `session` endpoint; `sessions()` gains `session_id`
- **Front-end**: First drill-down view (supersedes P4 "single pane, no drill-downs" product stance for this feature)
- **No schema migration**
- **REUSE.toml**: MIT pin for markdown-it artifact

### Invariants & Constraints
- Read-only `open_current()`; offline; no CDN; no bundler
- Composite identity `(harness, session_id)`; exact text on detail path
- Basic markdown only (markdown-it, no plugins, `html: false`)
- Non-goal: replace CLI `--detail raw`

## Open Questions

- [x] **Deep-link URL & client navigation** → Resolved: `/?view=session&harness=&session=` (see `memory-bank/active/creative/creative-deep-link-navigation.md`)
- [x] **Markdown library & HTML safety** → Resolved: markdown-it UMD, `html: false`, no plugins (see `memory-bank/active/creative/creative-markdown-library.md`)
- [x] **Reconstruction content model** → Resolved: nested tool_calls + MD/JSON export (see `memory-bank/active/creative/creative-reconstruction-content.md`)

## Test Plan (TDD)

### Behaviors to Verify

- `sessions()` includes `session_id` alongside existing fields; still excludes subagents; still snippet-truncates `prompt`
- `session_detail(harness, session_id)` → metadata + messages ordered by `ordinal` with full `text` (no truncation)
- Nested `tool_calls` ordered by tool ordinal; `tool_input` preserved as JSON-compatible structure
- Missing session → empty/not-found signal the server maps to 404
- Subagent session is returned by detail when addressed directly
- Server: `GET /api/session?harness=&session=` 200 with payload; missing params → 400; unknown session → 404
- Server serves vendored markdown-it static file with expected MIME
- Static HTML: markdown-it script local, loaded before dashboard module; no CDN
- Licensing: markdown-it artifact resolves MIT only (REUSE)
- JS: parse/build session view URL from `(harness, session_id)`; detect session view from `URLSearchParams`
- JS: build markdown export string from detail payload (role headings + fenced tool JSON)
- JS: markdown render helper uses `html: false` behavior (script tags escaped) — unit-testable if we wrap init in a pure module; otherwise covered by static config assertion + manual smoke
- Integration: Recent Sessions row is keyboard/click activatable toward session URL (static structure + JS URL helper; full DOM click optional)

### Test Infrastructure

- Framework: pytest (`skills/sr-search/tests/`), Node 22 `node --test` (`skills/sr-search/tests-js/`)
- Conventions: `_seed_session` helpers in `test_dashboard_metrics.py`; HTTP cases in `test_dashboard_server.py`; offline asset order in `test_dashboard_static.py`; pure ESM tests for core/data modules
- New / extended files:
  - Extend `tests/test_dashboard_metrics.py` (session_id + `session_detail`)
  - Extend `tests/test_dashboard_server.py` (`/api/session`, static markdown-it)
  - Extend `tests/test_dashboard_static.py` (load order, session pane landmarks)
  - Extend `tests/test_licensing.py` (markdown-it MIT)
  - New `tests-js/dashboard-session.test.mjs` (URL helpers + markdown export builder)
  - Possibly extract pure helpers into `dashboard-session.mjs` for testability

### Integration Tests

- Server metrics wiring: endpoint registry + query parsing for required session params
- Static + licensing: vendored file present and annotated

## Implementation Plan

1. **Extend `sessions()` wire + tests** (TDD)
    - Files: `metrics.py`, `tests/test_dashboard_metrics.py`
    - Changes: include `session_id` in each list record; update assertions

2. **Add `session_detail()` + tests** (TDD)
    - Files: `metrics.py`, `tests/test_dashboard_metrics.py`
    - Changes: query session row + messages + tool_calls; nest tools; full text; not-found → `None`
    - Creative ref: `creative-reconstruction-content.md`

3. **Wire HTTP `/api/session`** (TDD)
    - Files: `server.py`, `metrics.ENDPOINTS`, `tests/test_dashboard_server.py`
    - Changes: parse required `harness` (single) + `session`; 400/404/200; do not apply date-window defaults

4. **Vendor markdown-it 14.1.0 + REUSE** (TDD on licensing/static first where possible)
    - Files: `static/markdown-it-14.1.0.min.js` (from upstream `dist/markdown-it.min.js`), `REUSE.toml`, `tests/test_licensing.py`, `tests/test_dashboard_static.py`, `tests/test_dashboard_server.py`
    - Creative ref: `creative-markdown-library.md`

5. **Pure session front-end helpers + JS tests** (TDD)
    - Files: new `static/dashboard-session.mjs`, `tests-js/dashboard-session.test.mjs`
    - Changes: `buildSessionViewSearchParams`, `parseSessionViewParams`, `formatSessionMarkdownExport`, optional `renderMessageHtml(md, text)` wrapper

6. **Session pane UI + navigation** (TDD via static landmarks + helper tests; implement in `dashboard.mjs` / `index.html`)
    - Files: `index.html`, `dashboard.mjs`, `dashboard-data.mjs`
    - Changes: session pane markup; hide/show metrics vs session; fetch detail; markdown-it init; row click → `history.pushState`; boot from query; back control; collapsed tool `<details>`
    - Creative refs: deep-link + content model

7. **Export buttons**
    - Files: `dashboard.mjs` / `dashboard-session.mjs`
    - Changes: download JSON payload + markdown export blob

8. **Skills documentation**
    - Files: `skills/sr-dashboard/SKILL.md` (primary); brief cross-link note in `sr-search`/`sr-query` only if they already discuss session ids / full-text handoff
    - Changes: document URL template and when to offer it

9. **Verification**
    - `make test-js`, targeted pytest, then `make ci` (incl. REUSE)

## Technology Validation

**New dependency:** markdown-it **14.1.0** (MIT), vendored UMD `dist/markdown-it.min.js` (~124KB).

**PoC (2026-07-10):** Unpacked `npm pack markdown-it@14.1.0`; ran UMD under Node `vm` with `{ html: false, linkify: false, typographer: false }`; confirmed headings/emphasis/code fences render and raw `<script>` is escaped as text. **PASS** — safe to vendor this artifact during build.

No npm/bundler runtime; no other new technology.

## Challenges & Mitigations

- **Large `tool_input` JSON overwhelms UI**: collapsed `<details>` per tool; full content in export
- **Server endpoint arity differs from windowed metrics**: special-case `/api/session` params like existing `sessions`/`limit` branch; keep other endpoints unchanged
- **`session_id` URL encoding**: always use `URLSearchParams` / `encodeURIComponent`
- **XSS via transcript HTML**: markdown-it `html: false` (validated in PoC)
- **P4 "no drill-downs" docs/comments**: update skill + any stale comments; systemPatterns only if a durable pattern statement becomes wrong
- **JS DOM logic hard to pytest**: extract pure URL/export helpers to `dashboard-session.mjs` for Node tests

## Pre-Mortem

- **Plan failed because we treated session id as globally unique**: already constrained — composite key required in URL and API
- **Plan failed because markdown extensions crept in during build**: pin config in one init site + static test asserting no extra plugin script tags; export is the escape hatch
- **Plan failed because detail endpoint silently truncated text like the list view**: explicit invariant + tests asserting full text / no `…(+N)` markers on detail
- **Plan failed because path-based pretty URLs were assumed by skills**: creative chose query params; document exact template in `sr-dashboard` to prevent drift

## Status

- [x] Component analysis complete
- [x] Open questions resolved
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Pre-Mortem complete
- [ ] Preflight
- [ ] Build
- [ ] QA
