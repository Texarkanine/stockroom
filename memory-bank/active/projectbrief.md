# Project Brief

## User Story

As a contributor who already uses Stockroom, I want a presentation-quality Contributing guide that takes me from a normal install to hacking exclusively off my local checkout (and back again), so I can verify changes and return to the released/plugin install after I ship.

## Use-Case(s)

### Use-Case 1 — Enter localdev

I have Stockroom installed normally. I clone or open a checkout and follow Contributing to run exclusively from that checkout (torch, shim, harness plugin load, verification commands).

### Use-Case 2 — Hack and verify

I change engine/plugin/docs code, run the documented checks (`make ci`, docs build, reuse, ad-hoc engine invocation as needed), and confirm the harness is using my checkout — not the marketplace install.

### Use-Case 3 — Exit localdev

I finish (or abandon) the work and follow the reverse path back to the normal released/plugin install without leaving a half-broken hybrid state.

### Use-Case 4 — Notes accretion elsewhere

While drafting Contributing, material that belongs in Architecture or Advanced is parked as rough notes there so nothing is lost; those sections are not polished in this task.

## Requirements

1. Bring `docs/contributing/**` (and the root `CONTRIBUTING.md` funnel as needed) to the same reviewed quality bar as the accepted user guide.
2. Document the full localdev ritual set: `make torch`, `make localdev`, direct engine invocation, copy-into-plugin-dir (do not symlink for Cursor local plugin), shim ownership, and the reverse path back to a normal install.
3. Decide whether those enter/exit steps should be scripts (or Makefile targets) versus prose recipes — informed by prior archives and `/sr-search` over past Stockroom development sessions where localdev bit us.
4. Edits outside Contributing are allowed when something clearly belongs elsewhere during TLC; unfinished Architecture/Advanced may accrete rough notes only.
5. Home, user-guide, and Contributing (as we work it) must stay presentation-quality — no half-baked WIP left on finished surfaces.

## Constraints

1. Architecture and Advanced are out of polish scope for this run except as note sinks / ownership boundaries.
2. Do not reopen the archived `release-quality-docs` task id — this is a separate `/niko` run.
3. Preserve the leftover `memory-bank/active/creative/creative-embedding-invalidation.md` (unrelated); do not treat it as part of this task.
4. End-user install remains `sr-initialize` / marketplace — Contributing must not present `make`/`uv` as an alternative end-user bootstrap (per prior docs doctrine).

## Acceptance Criteria

1. A contributor can follow Contributing end-to-end: normal install → local checkout exclusive → verify → back to released/plugin install.
2. Non-obvious footguns from our own localdev history (archives + warehouse search) are captured where they belong.
3. Script-vs-recipe decision is explicit and reflected in the shipped guide (and code, if scripts win).
4. `make docs-build` (and other applicable gates) pass; Contributing pages are presentation-quality; Architecture/Advanced notes (if any) are clearly rough and do not break finished surfaces.
5. Operator accepts the Contributing section quality bar (same spirit as user-guide acceptance).

## Rework

Post-reflect design revision (operator, 2026-07-12). Implement the locked localdev model below; supersedes the shipped hybrid atoms where they conflict (notably `plugin-local` and takeover-only-for-dead).

### Rework user story

As a contributor, I want a rip-it-out enter path and a one-shot `make localdev` that wires skills, hooks, and the on-path shim to this checkout, so after uninstalling the marketplace plugin I am running exclusively from the checkout on next harness launch.

### Rework requirements

1. **Docs:** Rewrite `docs/contributing/local-workflow.md` — canonical "rip it out" story first (warehouse backup → uninstall plugin → stop dashboard → `HARNESS=… make localdev`), then appendix for modular `local-*` atoms and FORCE warnings.
2. **Delete `plugin-local`** from Makefile, docs, troubleshooting/cross-links, techContext/systemPatterns if they mention it.
3. **Shim FORCE:** Add force capability so `make shim TAKEOVER=1 FORCE=1` / `make local-engine` can replace a *live* foreign bake. Two-key turn; downplayed outside localdev/recovery; not agent-default.
4. **Thin Make atoms:** `local-skills`, `local-engine`, `local-dashboard`; `make localdev` only composes them. Harness-dependent targets require `HARNESS=cursor|claude` and error if unset. **No hook-install automation** — committed hooks need `*_PLUGIN_ROOT`; after uninstall that is unset. Docs carry a manual note for contributors changing the hook bootstrap surface only.
5. **`localdev-clean` / `localdev-status`:** Clean undoes only that harness’s localdev-managed artifacts (not warehouse, not marketplace, not shim). Status separates localdev-managed vs shim informational.
6. **No** `stockroom dashboard stop/restart` in this rework — rely on existing identity-aware dashboard replace.
7. **Throw out** mega-`localdev` inlined recipe, `hooks/localdev_hooks.py`, and dual-harness/project-hook Make wiring (nk-refresh 2026-07-12).

### Rework constraints

- Preserve end-user succeed-or-refuse shim policy for agents/skills (FORCE is opt-in and warned).
- Preserve unrelated `creative-embedding-invalidation.md`.
- Prior reflection remains historical; new creative/plan as needed for FORCE + hooks-in-localdev.
