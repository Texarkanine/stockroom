# Tasks: Phase 4 — Dashboard (`p4-dashboard`)

L4 project — work is decomposed into the milestone list in `memory-bank/active/milestones.md` (m1 API server → m2 vendored front-end → m3 launch surfaces). Each milestone runs as its own L1/L2/L3 sub-run with its own plan; this file is re-populated per sub-run.

## Preflight Findings (L4 milestone-list validation, 2026-07-09)

Status: **PASS with advisories** — no blocking findings; the items below are recorded for the relevant sub-runs to address.

1. **[m1 — must-address in sub-run design] Hook-launched dashboard vs. the lazy migration gate.** `warehouse.open(read_only=True)` runs the lazy migration gate — a reader behind the schema head *transparently becomes the migrator* (see `techContext.md` → Query). The hook-discipline invariant ("never migrates") therefore cannot be satisfied by simply opening read-only. m1 must decide how the dashboard behaves when the warehouse is behind the schema head (e.g. a gate-bypassing open that degrades to an "upgrade needed" response, rather than migrating). This is a design decision for the m1 sub-run's creative/plan phase, not a milestone-list defect.
2. **[m2 — required scope, already in invariants] REUSE annotation for vendored assets.** `REUSE.toml`'s layered licensing labels non-code `skills/**` paths PPL-S, and its code re-assert list (`*.py`, `*.sh`, `*.sql`, …) does not cover `*.js`/`*.html`/`*.css`. Vendored Chart.js (MIT, third-party) and the dashboard front-end must get explicit annotations so `reuse lint` stays green and upstream copyright is honored.
3. **[m3 — noted] Hook payload shape.** The existing sessionStart hooks carry the sanctioned raw `shim rectify` incantation (the shim may not exist/be stale at hook time). The dashboard launch must chain *after* rectify and go through the on-path `stockroom dashboard` (per roadmap); `test_skill_hygiene.py` extends to `sr-dashboard`. Planning-doc port corrections cover both `planning/roadmap.md` and `planning/tech-brief.md` (3143 → 6767).
4. **[all — caution] Clean-room posture toward `cursor-warehouse`.** The operator offered its dashboard as a reference, but `systemPatterns.md` flags it as itself a port of `claude-warehouse`. Use it for *shape* (server structure, idempotent startup, chart layout); write stockroom's metrics SQL from `dashboard-spec.md` and stockroom's own schema, not by copying queries.

### Advisory (optional, operator's call)

5. **[m1] Windowed endpoints as the recap substrate.** The roadmap says metrics are "designed as the time-series substrate for the post-v1 recap." A cheap concrete form: give the endpoints optional `?since=`/`?until=` window parameters (defaulting to the spec's 30d/14d windows) so the future recap is literally a client of the same endpoints dragged through time. Small addition if done in m1; retrofit later is also viable.
6. **[m1/m3] Daemonization lives in tested Python.** Put the detach/port-probe/fire-and-forget logic in the `stockroom.dashboard` CLI (not in hook shell), so the hook body stays a one-liner and idempotency is unit-testable — consistent with "the shim does plumbing, the dispatcher owns logic."
