# Project Brief: Phase 4 — Dashboard

Deliver **Phase 4 — Dashboard** of `planning/roadmap.md`: the v1 headline UI and the metric substrate the future recap will be dragged through time.

## User Story

As the stockroom operator, I want an at-a-glance local dashboard over my cross-harness warehouse — served fresh from the DB on every refresh — so that I can see what I've been up to across Cursor, Claude Code, and any future harness without running queries by hand.

## Requirements

Per the roadmap's two Phase 4 milestones:

1. **Metrics + local server + vendored front-end**
   - A light, stdlib-class Python web server (framework is the build-time pick; prior art is `cursor-warehouse`'s `dashboard.py`: `http.server` + duckdb, read-only) computing at-a-glance usage and activity metrics over the warehouse.
   - Served read-only on **port 6767** (operator override of the roadmap's 3143 — roadmap text should be corrected in-phase).
   - Every front-end asset vendored into the repo — no CDN — honoring the offline/supply-chain posture. Chart.js (pinned UMD bundle) is the approved single front-end dependency.
   - Metrics designed as the time-series substrate for the post-v1 recap.
2. **`sr-dashboard` + session-start hook**
   - A `dashboard` subcommand added to the `python -m stockroom` dispatcher; every launch path invokes it via the on-path `stockroom` shim.
   - `skills/sr-dashboard/` — a thin wrapper skill (like `sr-query`/`sr-semantic`) that launches on demand and prints the local URL.
   - A single session-start hook for **both harnesses** (Cursor + Claude Code) that launches the dashboard and nothing else: idempotent (probe the port, exit cleanly if already running), fire-and-forget (detached background process), bounded by the hook timeout, constitutionally unable to error, and never ingesting or migrating.

## Design Guides (not law)

- **Visual/behavioral guide:** `planning/brainstorm/Cross-harness Warehouse (standalone).html` — harness dropdown selector, Aggregate/Compare switcher, KPI cards, daily activity, sessions by project, tool distribution, write/read ratio, session efficiency, model distribution, first-prompt quality, recent-sessions table, wrapped banner.
- **API/behavior spec:** `planning/brainstorm/dashboard-spec.md` — endpoint shapes and the cross-harness rules: open harness set (`SELECT DISTINCT harness`, never hard-coded), positional signature colors assigned client-side from the fixed palette, server always returns per-harness data (Aggregate/Compare is a client concern), selection via repeatable `?harness=` filters, averages recomputed (never averaged-of-averages).
- **Prior art:** `../cursor-warehouse/scripts/dashboard.py` + `static/index.html` — the tight, small, self-contained shape to emulate (but stockroom vendors Chart.js instead of using a CDN).

## Explicit Scope Decisions

- Single-pane dashboard only; **no drill-downs** (conversation reconstruction explicitly deferred by the operator as feature-creep).
- Server code lives **in the engine package** (`skills/sr-search/src/stockroom/`), importable by the dispatcher and running inside the locked uv environment; `sr-dashboard` is a thin SKILL.md wrapper — confirmed with the operator over housing the server in the skill directory.
- Tokens/cost cards stay out (Cursor reports no per-message tokens); subagent and git-branch metrics are noted future Compare-mode additions, not v1.
- The hook never ingests and never migrates.

## Done When

The dashboard renders real metrics fully offline, `sr-dashboard` reliably surfaces the URL, and the session-start hook launches it exactly once regardless of how many sessions start — never erroring, never blocking session start, never touching the schema.
