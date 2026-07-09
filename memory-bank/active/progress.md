# Progress

Deliver Phase 4 — Dashboard of `planning/roadmap.md`: a read-only local web server (port 6767, operator override) computing cross-harness metrics over the warehouse with a fully vendored front-end (Chart.js pinned, no CDN) guided by the mockup and `dashboard-spec.md`; plus a `stockroom dashboard` dispatcher subcommand, a thin `sr-dashboard` wrapper skill, and idempotent fire-and-forget session-start hooks for both harnesses. Full brief in `memory-bank/active/projectbrief.md`.

**Complexity:** Level 4

## 2026-07-09 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - Intent clarification: restatement approved by operator with port override (6767 instead of the roadmap's 3143)
    - Reviewed the mockup (rendered in browser), `dashboard-spec.md`, cursor-warehouse's `dashboard.py`/`index.html` prior art, and the Phase-3 shim/dispatcher contract
    - Complexity determined: Level 4, matching the milestone-decomposed shape of Phases 1–3
    - Ephemeral memory bank files created (`projectbrief.md`, `activeContext.md`, `tasks.md`, `progress.md`)
* Decisions made
    - Port 6767 (operator)
    - Chart.js vendored as a pinned UMD bundle — the single approved front-end dependency (spec's "no external deps" reads as a backend constraint)
    - Session-start hook wired for both harnesses (Cursor + Claude Code), each a `stockroom dashboard` one-liner
    - Dashboard server code lives in the engine package (`skills/sr-search/src/stockroom/`), inside the locked uv env and importable by the dispatcher; `skills/sr-dashboard/` is a thin wrapper skill — operator confirmed over skill-directory colocation
    - Single-pane only; drill-downs (e.g. conversation reconstruction) explicitly deferred
* Insights
    - The spec's cross-harness rules (open harness set, positional client-side colors, per-harness server payloads, client-side Aggregate/Compare) keep every endpoint mode-agnostic — a clean server/client split worth preserving in the plan
    - Model grain differs per harness (`messages.model` vs `sessions.models[]`); the spec recommends session grain as the canonical, comparable grain

## 2026-07-09 - L4 PLAN - COMPLETE

* Work completed
    - Milestone list generated: m1 metrics API server (est. L3), m2 vendored front-end (est. L3), m3 launch surfaces (est. L2) — serial dependency order (m1 → m2 → m3)
    - Cross-milestone invariants recorded in `milestones.md` (read-only warehouse, fully offline/vendored, mode-agnostic per-harness endpoints, port 6767, invocation contract + skill hygiene, hook discipline, single pane, test-first)
* Decisions made
    - Server/front-end split into two milestones: the API contract (spec's JSON shapes) is the testable seam between them, letting m1 be delivered and verified headless before any UI work
    - Launch surfaces (dispatcher, skill, hooks) grouped into one small m3 since all three are thin, pattern-following artifacts over the m1 server
* Insights
    - The spec's "server returns per-harness data, client aggregates" rule means m1's endpoint tests need no mode logic at all — mode handling is entirely an m2 concern

## 2026-07-09 - L4 PREFLIGHT - COMPLETE (PASS with advisories)

* Work completed
    - Milestone list validated against codebase reality: conventions (engine-package placement, wrapper-skill shape, hook mechanism), dependency touchpoints (`warehouse.open`, `test_skill_hygiene.py`, REUSE.toml, both hook configs, both planning docs), and requirement coverage (both roadmap milestones + port correction mapped to m1–m3)
    - Findings recorded in `tasks.md`; `.preflight-status` written (PASS)
* Decisions made
    - m3 scope extended to correct the port in `planning/tech-brief.md` as well as the roadmap (both say 3143)
* Insights
    - The lazy migration gate inside `warehouse.open(read_only=True)` conflicts with the "hook never migrates" discipline — a reader behind the schema head becomes the migrator; m1 must design a non-migrating open/degrade path for the dashboard
    - `REUSE.toml`'s code re-assert list doesn't cover `*.js`/`*.html`/`*.css` under `skills/**`, so vendored front-end assets need explicit annotations (m2)

## 2026-07-09 - L4 PLAN REVIEW (operator) - COMPLETE

* Work completed
    - Preflight findings and advisories reviewed with the operator; all dispositions recorded in `tasks.md` and folded into `milestones.md`
    - Finding 1 (migration gate vs. hook discipline) explained and confirmed as an m1 must-address: the dashboard needs a gate-bypassing open that refuses (typed error → friendly "run `stockroom migrate`" response) instead of transitively migrating on session start
* Decisions made
    - Advisory 5 accepted: m1 endpoints take optional `?since=`/`?until=` windows (spec defaults) as the recap substrate
    - Advisory 6 accepted with an operator testing constraint (now a cross-milestone invariant): test only our own logic where test ROI is sound; never prove-the-platform tests; flaky-by-nature behavior → manual smoke QA
    - Operator-proposed and accepted: one combined sequenced session-start hook per harness (rectify-then-launch in a single command; ordering between sibling hook entries is not harness-guaranteed); resource lock is the OS port bind, no lockfile
    - m2 REUSE approach confirmed: explicit carve-out annotations for vendored assets; Chart.js keeps its upstream MIT identity, never relicensed

