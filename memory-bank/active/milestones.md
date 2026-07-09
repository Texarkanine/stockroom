# Milestones: p4-dashboard

## Cross-milestone invariants & constraints

- **Read-only over the warehouse.** Every dashboard DB touch goes through `warehouse.open(read_only=True)`; no milestone adds a write path, ingest, or migration to any dashboard or hook surface. How the server keeps the reader-becomes-migrator behavior of `open()` out of the hook-launched path is an m1 design decision — but no dashboard path may mutate warehouse data, ever.
- **Fully offline at runtime.** No CDN, no network fetch; every front-end asset is vendored into the repo and REUSE-licensed (vendored Chart.js carries its upstream MIT annotation).
- **Endpoints are mode-agnostic and harness-open.** The server always returns per-harness data keyed by harness name (Aggregate/Compare is a client concern); the harness set is enumerated from the DB (`SELECT DISTINCT harness`), never hard-coded; signature colors are assigned client-side positionally from the fixed palette.
- **Port 6767 everywhere.** The roadmap's stated 3143 is corrected in-phase (operator override).
- **Invocation contract holds.** Engine calls outside the repo go only through the on-path `stockroom` command; no rendered artifact (hook payload, skill) carries a raw engine path or invocation plumbing — `test_skill_hygiene.py` extends to `sr-dashboard`.
- **Hook discipline (amended Phase-3 m2).** The session-start hook launches the dashboard and rectifies the shim only — never ingests, never migrates (transitively: no hook-spawned process migrates either), never errors, never blocks. One combined hook per harness guarantees rectify-before-launch sequencing; idempotency is structural (the OS port bind is the mutex), not bookkeeping.
- **Test ROI discipline (operator, preflight review).** Unit-test our own logic only (probe decision, URL printing, argument handling, refusal paths); never write tests that prove the platform works (e.g. that Python can daemonize). Where a code test would be flaky-by-nature, manual smoke verification in the sub-run's QA is the sanctioned alternative.
- **Single pane, no drill-downs.** Conversation reconstruction and other drill-ins are explicitly out of scope (operator decision); mockup and spec are guides, not law.
- **Test-first for all Python; green `make ci` (incl. REUSE) at every milestone boundary.**

## Execution Order

- [ ] m1 — Dashboard metrics API server: `stockroom.dashboard` module serving the spec's per-harness JSON endpoints (overview, trends, projects, tools, models, efficiency, sessions, wrapped) read-only on port 6767 with `?harness=` filtering and optional `?since=`/`?until=` windows (spec defaults), a non-migrating open path (typed refusal when the schema is behind), static-file serving, and port-probe idempotent startup
- [ ] m2 — Vendored single-pane front-end: `index.html` + pinned Chart.js committed to the engine package (REUSE carve-out annotations; Chart.js keeps its upstream MIT identity, never relicensed), with harness dropdown selector, Aggregate/Compare switcher, positional color palette, KPI cards, charts, recent-sessions table, and wrapped banner per the mockup guide
- [ ] m3 — Launch surfaces: `dashboard` subcommand registered in the `python -m stockroom` dispatcher, thin `sr-dashboard` wrapper skill printing the local URL, one combined sequenced session-start hook per harness (rectify-then-launch in a single command; port bind is the mutex), and the planning-doc port corrections (roadmap + tech-brief: 3143 → 6767)

## Milestone Estimates

- **m1 — estimated L3.** A new engine component (server + eight query-backed endpoints) built test-first against the warehouse; multiple modules touched (`dashboard`, tests, fixtures) but no architectural change — it consumes established chokepoints.
- **m2 — estimated L3.** A complete self-contained front-end (selector, mode switcher, seven visual panels) plus the vendoring/licensing pass; substantial but isolated to static assets served by m1.
- **m3 — estimated L2.** Three small, pattern-following artifacts: a one-line dispatcher registration, a thin wrapper skill in the established `sr-*` shape, and hook entries mirroring the existing Phase-3 hook mechanism.
