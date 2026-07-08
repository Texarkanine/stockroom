# Decision: Roadmap Resequencing — Onboarding/CLI Before Dashboard

## Context

**What**: With Phase 2 archived, the roadmap says Phase 3 (Dashboard) is next. Two brainstormed items are not yet on the roadmap: the on-path `stockroom` CLI (`planning/brainstorm/stockroom-on-path-cli.md`, slated for Phase 4 per its own sequencing section) and the wrapper-skill litter trimming pass (`planning/brainstorm/skill-litter-audit.md`, sequenced after the CLI lands). The question: should the roadmap be adjusted — phases inserted, amended, or re-ordered — before starting the next phase?

**Why it matters**: Every artifact authored before the CLI exists inherits the fragile four-part invocation incantation (a proven drift source — the m4 bug found it wrong in three mutually-agreeing places at once). And every artifact *rendered outside the repo* (shim, cron entry, launchd plist) carries a second, worse risk: plugin updates move the versioned cache directory, silently stranding anything that baked an absolute path. Ordering determines how many artifacts must be retrofitted versus authored clean.

**Constraints**:
- Phases are ordered by dependency, not calendar (roadmap's own rule).
- "Onboarding wraps proven parts" — `sr-initialize` should orchestrate capabilities that already work (Sequencing Principles).
- The CLI's brainstorm doc places shim + dispatcher inside `sr-initialize`'s existing "prerequisites and torch" scope; the litter audit sequences its trimming pass after (or with) the CLI.
- The v1 spine and Phase 5's end-to-end test are fixed; whatever order is chosen, all four surfaces must exist before Phase 5.
- TDD binds the dispatcher (tested Python); the shim stays too dumb to need tests.

## Options Evaluated

- **Option A — Keep the order**: Dashboard next as written; CLI + trimming land in Phase 4 per the brainstorm docs; `sr-dashboard` and the session-start hook are authored against the current incantation and trimmed later.
- **Option B — Swap Phases 3 and 4**: Onboarding/Scheduling (amended to absorb shim + dispatcher + the update-drift resolution + the trimming pass) runs next; Dashboard follows, authored lean against the `stockroom` CLI contract.
- **Option C — Insert a mini-phase**: a small "Invocation Consolidation" phase (dispatcher + shim + trimming) between Phase 2 and Phase 3; Dashboard and Onboarding keep their relative order.
- **Option D — Pull the CLI into Phase 3**: Dashboard phase grows a first milestone building shim + dispatcher, then builds the dashboard on top.

## Analysis

| Criterion | A (keep) | B (swap) | C (mini-phase) | D (CLI into P3) |
|-----------|----------|----------|----------------|-----------------|
| Litter avoided (author lean vs trim later) | ✗ — sr-dashboard + hook inherit incantation, 4th/5th copies | ✓ — dashboard authored against `stockroom …` | ✓ | ✓ |
| Rendered-artifact drift solved before more artifacts exist | ✗ — hook ships before drift story exists | ✓ — solved once in onboarding; cron targets the shim | ~ — shim exists but its owner/installer (`sr-initialize`) doesn't | ~ — CLI ownership lands in the wrong phase |
| "Onboarding wraps proven parts" principle | ✓ | ✓* — everything `sr-initialize` orchestrates (torch, ingest, embed, schedule) is Phase 1–2 proven; it never orchestrated the dashboard anyway | ✓ | ✓ |
| Shim has a natural installer | ✓ (P4) | ✓ (same phase) | ✗ — needs an installer before `sr-initialize` exists; `make shim` covers dev only | ✗ — same problem, buried in the dashboard phase |
| Time to "clean, usable, you-can-search" for a fresh install | ✗ — deferred behind dashboard | ✓ — next phase delivers it | ~ | ✗ |
| Dashboard usefulness at birth | ✗ — renders over a manually-maintained warehouse | ✓ — renders over a nightly-fresh, fully-embedded warehouse | ✗ | ✗ |
| Phase scope balance | ✓ | ~ — onboarding phase grows; mitigated by L4 sub-run structure (Phase 2 precedent) | ✓ | ✗ — dashboard phase becomes two unrelated projects |

Key insights:

- **The P3→P4 dependency edge is nominal.** Phase 4's milestones never touch the dashboard — `sr-initialize` checks prerequisites, provisions torch, schedules, and runs first ingest/embed. Swapping breaks no real dependency; the mermaid edge overstates the coupling.
- **The cron entry is the drift problem's sharpest edge, and the shim is its answer.** A crontab line pointing into a versioned plugin cache silently stops ingesting after the first update — worse than the shim's own staleness, because nothing on the user's PATH even exists to self-heal it. If the nightly job invokes `stockroom ingest` / `stockroom embed` *via the shim*, the entire drift-defense surface collapses to one regenerable file with verify-then-re-resolve logic. This resolves the brainstorm's line-32 TODO structurally: rendered-out artifacts never bake engine paths; only the shim does, and the shim self-heals. That coupling (scheduling must target the shim) is itself an argument that shim and scheduler belong in the same phase, shim first.
- **The session-start hook is in-plugin, not rendered-out** — it ships in the manifest and updates with the plugin — but its *body* still needs to invoke the engine. Built after the CLI it is a one-liner (`stockroom dashboard`, idempotent by port-probe); built before, it is a fifth copy of the incantation inside a hook that is constitutionally forbidden to error.
- **The project's own archive already scored this experiment.** m4/m5 (authored before the lean constraint) carry Category A–C litter awaiting a trimming pass; m6 (authored under it) shipped with zero plumbing and needed no rework. Option A deliberately re-runs the losing arm.
- **Option C's fatal flaw is ownership**: the brainstorm's core insight is that invocation plumbing is an *onboarding* concern — the initializer is the one component that must already understand how the system works. A shim without `sr-initialize` has no user-facing installer, and building half of `sr-initialize` early is just Option B with extra phase boundaries.

## Decision

**Selected**: Option B — swap Phases 3 and 4, amending the onboarding phase to absorb the CLI and the trimming pass.

**Rationale**: The swap costs nothing real (the P3→P4 edge is nominal; "wraps proven parts" holds for everything `sr-initialize` actually orchestrates) and buys three things at once: the dashboard and its hook are authored lean against a stable one-word contract instead of joining the trimming backlog; the rendered-artifact drift problem is solved once, at the moment the *first* rendered-out artifacts (shim, cron entry) are created, rather than retrofitted; and a fresh install reaches the product's core promise — a populated, embedded, nightly-fresh, searchable warehouse — one phase sooner. The dashboard also becomes *more* valuable by moving later: metrics over a nightly-fresh warehouse are trustworthy; metrics over a manually-poked one are decoration.

**Tradeoff**: The onboarding phase grows (torch validation on real machines + shim + dispatcher + drift resolution + scheduling + first run + trimming pass) — accepted because the L4 sub-run structure absorbed exactly this scale in Phase 2. The spine's "open the dashboard" first-run payoff is deferred one phase — accepted explicitly by the operator ("bell/whistle"). And the dispatcher will gain a `dashboard` subcommand one phase after it is born — an addition, not a rework.

## Implementation Notes

Roadmap amendment (a conscious edit to `planning/roadmap.md`, per that doc's own "roadmap amendment" hook in the CLI brainstorm):

- **New Phase 3 — Onboarding, CLI, and Scheduling** (formerly Phase 4, amended). Suggested milestone shape:
  1. `sr-initialize` — prerequisites, torch, **and the on-path CLI**: prerequisite checks, platform/accelerator detection, torch provisioning + smoke test, plus the `python -m stockroom` dispatcher (tested) and the `~/.local/bin/stockroom` shim (generated, verify-then-re-resolve). The update-drift question (brainstorm line-32 TODO) is *decided here* — resolution order, staleness detection, re-resolution strategy.
  2. `sr-initialize` — scheduling and first run: cron/launchd entries **invoke the shim** (`stockroom ingest`, `stockroom embed`) — no raw engine paths in any rendered-out artifact; then first full ingest + embed.
  3. **Wrapper-skill trimming pass**: swap incantations for `stockroom <subcommand>` across `sr-query`/`sr-semantic`/`sr-search`, apply the litter-audit inventory, add the shared reference doc + pointers, re-run the m6 grep-verifiable no-invocation-token check.
- **New Phase 4 — Dashboard** (formerly Phase 3, content unchanged except): `sr-dashboard` and the session-start hook are specified against the `stockroom` CLI (hook body ≈ idempotent `stockroom dashboard`); the dispatcher gains the `dashboard` subcommand here.
- **Phase 5 unchanged**, and slightly *shrunk* as the CLI brainstorm predicted: engine invocation stops being per-harness (PATH is PATH), leaving only skill-invocation forms (`/sr-*` vs `<plugin>:<skill>`) to verify empirically.
- Update the mermaid graph (P2 → onboarding → dashboard → P5) and the "Onboarding wraps proven parts" sequencing principle to note the deliberate exception: onboarding now *precedes* the dashboard because it owns the invocation/drift substrate the dashboard builds on.
- Both brainstorm docs' "Feeds:" headers and sequencing sections should be updated to reflect the new phase numbering when the amendment is applied.
