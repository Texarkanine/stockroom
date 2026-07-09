---
task_id: p4-dashboard
complexity_level: 4
date: 2026-07-09
status: completed
---

# TASK ARCHIVE: Phase 4 — Dashboard

## SUMMARY

Phase 4 delivered stockroom's v1 local dashboard: a read-only metrics API and vendored single-pane front-end over the cross-harness warehouse, plus the launch surfaces that make it appear without ceremony. The operator gets an at-a-glance view across Cursor, Claude Code, and any future harness — served fresh from DuckDB on every refresh, fully offline, on port 6767.

The architectural spine is a **non-migrating read path** (`warehouse.open_current()`) feeding eight mode-agnostic JSON endpoints, a client that owns Aggregate/Compare and positional harness colors, and thin launch wiring that reuses the Phase-3 on-path `stockroom` contract. Session-start hooks rectify the shim then launch the dashboard in one silenced command; the OS port bind is the idempotency mutex.

Delivered as a Level 4 project across three sequential milestones (m1 L3 → m2 L3 → m3 L2). Every milestone landed to plan; m1 and m2 each absorbed one substantive QA remediation before a clean second pass; m3 was clean on the first QA.

## REQUIREMENTS

From `projectbrief.md` (Phase 4 of `planning/roadmap.md`):

1. **Metrics + local server + vendored front-end**: stdlib-class Python server computing at-a-glance metrics read-only on port 6767 (operator override of roadmap 3143); every front-end asset vendored (pinned Chart.js UMD); metrics designed as the time-series substrate for the post-v1 recap.
2. **`sr-dashboard` + session-start hook**: `dashboard` on the `python -m stockroom` dispatcher; thin `sr-dashboard` wrapper skill printing the local URL; one combined session-start hook per harness that launches only — idempotent, fire-and-forget, never ingesting or migrating, constitutionally unable to error.

### Cross-milestone invariants (held throughout)

- **Read-only over the warehouse** — every DB touch via `warehouse.open(read_only=True)` / `open_current()`; no dashboard path mutates data or schema.
- **Fully offline at runtime** — no CDN; Chart.js vendored with upstream MIT REUSE annotation.
- **Endpoints mode-agnostic and harness-open** — per-harness JSON keyed by harness name; harness set from `SELECT DISTINCT harness`; Aggregate/Compare and signature colors are client concerns.
- **Port 6767 everywhere**; planning docs corrected in-phase.
- **Invocation contract holds** — engine calls outside the repo go only through on-path `stockroom`; hygiene test extended to `sr-dashboard`.
- **Hook discipline** — rectify-then-launch in one command; never ingest, migrate, error, or block; port bind is the mutex.
- **Single pane, no drill-downs**; test-first Python; green `make ci` (incl. REUSE) at every milestone boundary.

## IMPLEMENTATION

### Milestone list (as planned, as executed)

The three milestones executed in the planned serial order with **no additions, removals, re-scoping, or reordering** at the project level. Estimated levels held (m1 L3, m2 L3, m3 L2). One public-boundary amendment landed inside m2's QA rework (`prev_distinct_projects`) — a completion of the Projects KPI contract, not a new milestone.

- [x] **m1 — Dashboard metrics API server (L3)**
- [x] **m2 — Vendored single-pane front-end (L3)**
- [x] **m3 — Launch surfaces (L2)**

### Sub-run summaries

#### m1 — Dashboard metrics API server (L3)

Built the complete local dashboard backend: observation-time schema (`0004` + ingest carry-forward of `first_seen_at`), non-migrating `open_current()`, eight metric endpoints (overview, trends, projects, tools, models, efficiency, sessions, wrapped), loopback HTTP/static serving, and idempotent CLI startup with port-probe.

Key decisions: `COALESCE(started_at, source_mtime)` for Cursor visibility without fabricating authored timestamps; separate `first_seen_at` observation grain for future recap; refusal (503) rather than migrate when schema is behind. QA caught a transport-policy bug — partial HTTP windows silently applied generic 30-day defaults that belonged to endpoint-owned policy — fixed by parsing bounds in transport and leaving defaults to metrics. Full gate: 402 tests after remediation.

#### m2 — Vendored single-pane front-end (L3)

Delivered the offline single-pane UI: open harness discovery, positional colors, client-owned Aggregate/Compare, KPI cards, seven chart panels, recent sessions, wrapped banner, vendored Chart.js 4.5.1 with precise REUSE ownership, Node 22 contracts, no package manager or build path.

First QA failed on two substantive blockers: Projects KPI delta compared distinct current values to summable previous counts, and canvas `aria-label`s carried title/mode only instead of measured content. Rework amended the public boundary with `prev_distinct_projects` and moved chart summaries into tested pure modules. Second QA clean; live smoke confirmed Projects `+27%` and measured Aggregate/Compare summaries.

#### m3 — Launch surfaces (L2)

Wired the existing launcher into the dispatcher (`dashboard` in `SUBCOMMANDS`), thin `sr-dashboard` skill, and combined rectify-then-launch hooks per harness; corrected roadmap/tech-brief ports 3143 → 6767. Chicken-egg heal kept: plugin-root bootstrap for `shim rectify`, on-path `stockroom dashboard` for launch, one silence wrapper. Hygiene briefly failed when negative guidance named forbidden tokens — rephrased. QA found no code defects; updated stale persistent docs in-phase. `make ci` green (411 pytest / 3 skipped, 32 JS, ruff, REUSE); manual smoke confirmed idempotent URL printing.

### Key artifacts created

- `src/stockroom/dashboard/` — metrics, HTTP server, CLI launcher, static assets (`index.html`, vendored Chart.js).
- Migration `0004` + ingest observation-time carry-forward for `first_seen_at`.
- `warehouse.open_current()` — non-migrating read chokepoint reusable by future local read surfaces.
- `skills/sr-dashboard/SKILL.md` — thin wrapper printing the local URL.
- Combined session-start hooks (Cursor + Claude Code) — `{ rectify; stockroom dashboard; }` silenced.
- Planning-doc port corrections (roadmap + tech-brief → 6767).

### Design decisions of record

- **Non-migrating open** — availability separated from schema mutation; hook-launched dashboard can start without a warehouse and refuses cleanly when stale.
- **Server always returns per-harness data** — Aggregate/Compare is purely client-side; averages recomputed, never averaged-of-averages.
- **Contract-first native front-end** — pure ESM modules tested under Node; adapter applies DOM; no bundler.
- **Chicken-egg hook** — rectify cannot be on-path-only when a dead `APP_DIR` makes `stockroom` itself unusable; launch uses the healed shim.
- **Structural idempotency** — OS port bind is the mutex; no bookkeeping file.

## TESTING

Every milestone gated by `make ci` (pytest + JS where applicable + ruff + lock check + REUSE) and TDD for Python (and Node contracts for the front-end).

- **m1**: Red-first across schema, ingest, warehouse open, metrics, server, CLI; QA remediation for partial-window transport policy; second review + 402-test gate green. Manual: stale-schema refusal does not mutate.
- **m2**: Staged TDD + browser pass for packaging, races, theme, offline; first semantic QA FAIL → five-step rework TDD → clean second QA; live-warehouse smoke for Projects delta and canvas summaries.
- **m3**: Linear red→green on dispatcher, skill hygiene, packaging (incl. on-path launch and port-doc contracts); first QA PASS; manual smoke for idempotent URL printing and dispatcher help.

## SYSTEM STATE

What exists now that didn't before:

- **A local dashboard** at `http://127.0.0.1:6767/` — eight JSON endpoints + vendored single-pane UI over the real warehouse, fully offline.
- **`open_current()`** — a reusable non-migrating read chokepoint for any future local read surface that must not migrate from a hook or daemon path.
- **Observation-time substrate** (`first_seen_at` + Cursor `source_mtime` fallback) — the time-series grain the post-v1 recap will drag through time.
- **`stockroom dashboard`** on the dispatcher (ninth subcommand alongside Phase-3's eight).
- **`sr-dashboard`** thin wrapper skill, hygiene-pinned like the other wrappers.
- **Session-start auto-launch** for Cursor and Claude Code — rectify-then-launch, never ingest/migrate/error/block.

End-to-end: open a harness session → hook heals the shim if needed → dashboard binds or reuses port 6767 → operator refreshes a single pane of cross-harness metrics with no manual query and no network fetch.

### Acceptance criteria — met

1. Dashboard renders real metrics fully offline. ✔
2. `sr-dashboard` reliably surfaces the local URL. ✔
3. Session-start hook launches exactly once regardless of how many sessions start — never erroring, never blocking, never touching the schema. ✔

## LESSONS LEARNED

- **Parse syntax at transport; construct defaults in the endpoint that owns them.** A generic HTTP default is policy, not parsing — m1's partial-window bug was the textbook case.
- **Non-summable KPIs need a previous-window rollup of the same grain** before any client delta is planned; per-harness previous counts are not a substitute for a filtered distinct union (m2 Projects).
- **Canvas accessibility is a content contract**, not attribute presence — measured values (or an explicit no-data sentence) belong in pure tested code.
- **Session-start heal cannot be on-path only** when a dead baked path makes the shim itself unusable; keep plugin-root rectify, launch via healed on-path command.
- **Wrapper-skill hygiene is a literal substring scan** — even “don't use PYTHONPATH” prose fails; phrase negatives without naming forbidden tokens.
- **`open_current()` is a reusable architectural capability**, not a dashboard exception — future local read surfaces should reuse it rather than bypass warehouse policy.

## PROCESS IMPROVEMENTS

- **Cross-cutting requirements need at least one boundary-level test** combining transport and domain behavior; isolated unit coverage can leave ownership errors invisible (m1).
- **A green first CI gate does not prove semantic KPI honesty** — challenge distinct-versus-summable comparisons and accessibility content before calling a dashboard milestone done (m2).
- **When QA fails on a missing contract, amend the public boundary narrowly** rather than hiding the trend or redefining the metric (m2 rework loop).
- **Soft “verify in build” steps for static docs are easy to under-test** — a tiny packaging assertion (port 6767) closed the gap without new infrastructure (m3).
- **File-impact planning should include a migration-head sweep** whenever a numbered migration is added (m1).

## TECHNICAL IMPROVEMENTS

- **Makefile exact-sync / Torch conflict** — full `make ci` still strips the intentionally out-of-lock Torch install; restoring the wheel and re-smoking remains a per-gate tax until the Makefile is made torch-safe (flagged in m1 reflect; still open).
- **Calendar-series bucket math** — fixed shapes should derive their first bucket from the last instant included by an exclusive end, not raw duration subtraction (m1 insight; already fixed in metrics).

## NEXT STEPS

None required — Phase 4 acceptance criteria are met. Natural continuations already deferred by the brief: conversation drill-downs, tokens/cost cards (when Cursor exposes them), subagent and git-branch Compare-mode metrics, and the post-v1 recap that will consume the observation-time substrate.

### Million-Dollar Question (across sub-runs)

Had launch surfaces been assumed from day one, the dispatcher entry, `sr-dashboard`, and combined hook would still look like what m3 shipped — thin wiring over a complete launcher. The elegant form is no second server entrypoint, no skill-side spawn logic, and one silenced command per harness with structural idempotency. Separately, m1's creative work established that non-migrating read and observation-time grains are foundational for any future local UI — worth treating as spine, not dashboard-only exceptions.
