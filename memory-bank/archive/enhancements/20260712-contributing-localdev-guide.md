---
task_id: contributing-localdev-guide
complexity_level: 3
date: 2026-07-12
status: completed
---

# TASK ARCHIVE: contributing-localdev-guide

## SUMMARY

Brought Contributing to user-guide presentation quality with a complete localdev enter / hack / verify / exit path. After an initial hybrid ship, two reworks landed the binding model: thin Make atoms composed by `HARNESS=… make localdev`, shim FORCE for live foreign takeover, **no** project-hook automation, and post-reflect polish that moved fat shell into `scripts/localdev.sh` and made `shim rectify` create when the dest is absent so exit no longer needs `sr-initialize` just to bind the shim.

## REQUIREMENTS

Original:

1. Presentation-quality `docs/contributing/**` (and CONTRIBUTING funnel) matching the accepted user-guide bar.
2. Document full localdev ritual: enter exclusive checkout use, verify, exit without hybrid half-state.
3. Decide scripts vs Makefile recipes vs prose — informed by archives + warehouse search.
4. Architecture/Advanced may only accrete rough notes; finished surfaces stay presentation-quality.
5. End-user install remains `sr-initialize` / marketplace — Contributing must not present `make`/`uv` as bootstrap.

Rework² (binding):

1. Rip-it-out enter story first; modular `local-*` appendix.
2. Delete `plugin-local`; always backup warehouse before enter.
3. Shim FORCE: live foreign needs `TAKEOVER=1 FORCE=1` (two-key); not agent-default.
4. Thin atoms: `local-skills`, `local-engine`, `local-dashboard`; composer `localdev`; harness-scoped targets require `HARNESS=cursor|claude`.
5. **No Make hook install** — `*_PLUGIN_ROOT` is unset after marketplace uninstall; docs note manual hooks only when changing the bootstrap surface.
6. `localdev-clean` / `localdev-status` semantics; no `dashboard stop/restart`.

Post-reflect polish:

1. Enter heal via `ensure-env` / freeze — not blind `make torch`.
2. Fat Make recipes → POSIX `scripts/localdev.sh`.
3. Clean unclaims `owner=dev` shim only; status reports real shim/torch facts.
4. `shim rectify` creates when dest absent (hook heal after wipe / localdev exit).

## IMPLEMENTATION

### Creative decisions (inlined)

**1. contributor-localdev-round-trip (Option D — Hybrid)**

Options: A prose-only, B full Make orchestration (`contrib-enter`/`exit`), C standalone scripts, D hybrid thin targets + narrative docs.

Selected **D**: named mechanical atoms in the Makefile; Contributing owns the ordered human story. Rejected silent mega-enter (warehouse `aef4448b` is a procedure; `bb1e3895` needed undo). First ship: `localdev-clean`, `plugin-local`, documented `shim TAKEOVER=1`, `local-workflow.md` SSOT for Enter/Verify/Exit.

**2. localdev-hooks-and-force (Option B then amended)**

Original rework creative selected PATH-based project hooks + FORCE two-key, with mega-`localdev` wiring skills+hooks+shim+dashboard.

**Composition amendment:** expose `local-skills` / `local-engine` / `local-dashboard`; `localdev` only composes; require `HARNESS`.

**Hooks amendment (binding):** drop project-hook *automation* entirely. Committed `hooks/*.json` need `*_PLUGIN_ROOT`; after uninstall that is unset — copying hooks into the project does not help. PATH-based hook *content* remains a valid manual pattern only.

nk-refresh during the interrupted mega-`localdev` build was the high-leverage correction: one-shot for the operator must mean a thin composer, not one opaque recipe body.

### Phases

1. **L3 initial** — Hybrid atoms + `local-workflow.md`; QA/Reflect COMPLETE.
2. **Rework** — FORCE + mega-localdev + hook helper; build interrupted at format gate.
3. **Rework²** — Delete `hooks/localdev_hooks.py` + tests; thin atoms + `HARNESS`; docs rip-it-out; M3–M9 gates; QA/Reflect COMPLETE.
4. **Post-reflect polish** — `scripts/localdev.sh`; status/clean semantics; rectify create-on-absent; exit docs drop initialize-for-shim.

### Key surfaces

| Area | Paths |
| --- | --- |
| Make orchestration | root `Makefile` (`require-harness`, `local-*`, `localdev`, `localdev-clean`, `localdev-status`, `shim` + `TAKEOVER`/`FORCE`) |
| Localdev shell | `scripts/localdev.sh` (POSIX; skills/clean/status) |
| Shim policy | `skills/sr-search/src/stockroom/shim.py` — FORCE on install; rectify create-if-absent / rebake-if-owned / never foreign |
| Docs | `docs/contributing/local-workflow.md`, `development.md`, troubleshooting cross-links, `CONTRIBUTING.md` funnel |
| Deleted | `hooks/localdev_hooks.py`, `tests/test_localdev_hooks.py`, `plugin-local` target |
| Persistent MB | `memory-bank/techContext.md`, `systemPatterns.md` (atoms + rectify create; no localdev hook install) |

### Locked atom inventory (final)

| Target | `HARNESS`? | Role |
| --- | --- | --- |
| `local-skills` | required | Wire checkout skills for that harness |
| `local-engine` | no | `shim TAKEOVER=1 FORCE=1` + `ensure-env` |
| `local-dashboard` | no | Bounce `stockroom dashboard` |
| `localdev` | required | Invokes the three atoms above |
| `localdev-clean` | required | Undo harness-managed bits + remove `owner=dev` shim |
| `localdev-status` | optional | Report managed vs shim sections |

Usage: `HARNESS=cursor make localdev` (or `claude`). Claude `local-skills` is a no-op + `--plugin-dir` reminder (no flat skills farm).

## TESTING

- Shim FORCE: S1–S5 (already green; preserved).
- Rectify create-on-absent: unit + CLI tests updated (`test_absent_dest_creates_shim`, CLI create exit 0); 29 shim tests passed at archive gate.
- Make checks M1–M9 (HARNESS guards, atom composition, no `local-hooks` / `localdev_hooks`, status separator, deleted helper).
- Docs: `make docs-build`; B2 no `plugin-local`; B3 rip-it-out + `HARNESS` + manual hooks footnote.
- Full `make format` / `make ci` green on rework² build (512 passed, 3 skipped).
- `/niko-qa` PASS (rework²: trivial projectbrief stale-hooks line only).
- No pytest theater for Makefile — shell/manual checks only (consistent with project stance).

## LESSONS LEARNED

- Make recipe lines are separate shells; harness branching must be one compound `if/else`, not early `exit 0` then more lines.
- Copying `hooks/*.json` into a project cannot fix missing `*_PLUGIN_ROOT` after marketplace uninstall — automation cannot paper over that.
- “One-shot for the operator” ≠ one opaque Make body; named atoms + thin composer preserve the first creative’s anti-mega-enter principle.
- When creative Implementation Notes diverge from a later operator amendment, preflight must name the binding text explicitly or build will resurrect dead design.
- Rectify never-create forced an awkward `sr-initialize` after localdev exit; create-on-absent aligns hook heal with the exit story.

## PROCESS IMPROVEMENTS

- nk-refresh mid-build is appropriate when shipping shape matches an outdated requirement letter but violates an earlier architectural principle.
- Preflight’s check-fail→implement amendment for Make atoms was the highest-leverage process catch on the initial plan pass — keep it for any Makefile-in-scope L3.
- Preserve unrelated leftover creatives explicitly in the projectbrief (here: `creative-embedding-invalidation.md`) so archive cleanup does not delete them.

## TECHNICAL IMPROVEMENTS

- Fat contributor shell belongs in `scripts/*.sh` with Make as the thin public interface — matches techContext “Makefile is the checkout entrypoint” without stuffing POSIX into recipe lines.
- Status that reports real shim header + torch beats a doctor pointer for half-state diagnosis.

## NEXT STEPS

1. Unrelated leftover creative remains active: `memory-bank/active/creative/creative-embedding-invalidation.md` — handle in its own `/niko` run when embedding invalidation is scoped.
2. Optional follow-ups outside this archive: further Claude/Cursor docs parity polish if operator WIP continues; Architecture/Advanced still deferred from `release-quality-docs`.
