---
task_id: contributing-development-guide
complexity_level: 2
date: 2026-07-14
status: completed
---

# TASK ARCHIVE: contributing-development-guide

## SUMMARY

Finished the Contributing day-to-day half: a surface-first Iteration guide (engine, Torch, docs site, dashboard, skills) that assumes Preparation enter/verify/exit is done. Post-reflect polish renamed the pages (`local-workflow` → `preparation`, `development` → `iteration`), inlined Make targets per section, split torch-safe dashboard tests (`test-dashboard-js` / `test-dashboard-py`), and restyled Skills to match the other surfaces.

## REQUIREMENTS

1. Day-to-day contributor guide assuming local checkout is wired; link enter/exit elsewhere.
2. Cover prerequisites, engine, Torch (restore vs try-new), docs site, dashboard, skills.
3. Keep Make target reference accurate and scoped to each surface (not one giant dump).
4. Do not re-own the localdev rip-it-out ritual.

## IMPLEMENTATION

| Area | Paths |
| --- | --- |
| Iteration guide | `docs/contributing/iteration.md` (was `development.md`) |
| Preparation guide | `docs/contributing/preparation.md` (was `local-workflow.md`) |
| Nav / funnel | `docs/contributing/.pages`, `index.md`, `CONTRIBUTING.md`, `licensing.md` |
| Make | `test-dashboard-js`, `test-dashboard-py`; `make test` depends on `test-dashboard-js`; dropped `test-js` |
| Persistent MB | `systemPatterns.md`, `techContext.md` (Development/Iteration ownership pointers) |

SSOT split: Preparation owns enter/verify/exit atoms; Iteration owns day-to-day loops; operator torch remedies stay in `docs/user-guide/troubleshooting/torch.md`.

## TESTING

Docs-only verification: content checklist against acceptance behaviors + `make docs-build`. Smoke-ran `make test-dashboard-js` and `make test-dashboard-py`. `/niko-qa` PASS (trivial polish only).

## LESSONS LEARNED

- Name `stockroom shim ensure-env` for Torch restore; “heal” blurs into `make torch`.
- Surface-first Iteration + Preparation enter/exit is the durable Contributing IA.
- After a large localdev docs task, finishing the paired day-to-day page as L2 is the right cut.

## PROCESS IMPROVEMENTS

None beyond keeping post-reflect operator polish in the same task until archive rather than opening a new L2 for renames alone.

## TECHNICAL IMPROVEMENTS

None required for this docs task. Persistent MB may still say “Development” in prose in places that mean Iteration — update surgically when next touched.

## NEXT STEPS

None for this task. Type `/niko` for new work.
