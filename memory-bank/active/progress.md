# Progress

Bring Contributing docs to user-guide quality with a complete localdev enter/hack/verify/exit path (and decide scripts vs recipes), informed by archives and warehouse search; park Advanced/Architecture leftovers as notes only.

**Complexity:** Level 3

## 2026-07-12 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - Validated intent with amendment: unfinished Architecture/Advanced may accrete rough notes; Home, user-guide, and Contributing must stay presentation-quality
    - Classified as Level 3
* Decisions made
    - Level 3 (not L2): open script-vs-recipe design question + multi-surface scope warrants creative/plan rigor; not L4 (not system-wide product redesign)
* Insights
    - Prior `release-quality-docs` archive explicitly deferred Contributing/Architecture/Advanced as separate runs; this task owns Contributing only

## 2026-07-12 - CREATIVE - COMPLETE (contributor-localdev-round-trip)

* Work completed
    - Researched archives + warehouse (`aef4448b` enter path, `bb1e3895` no undo, heal-after-move / p3 / p5)
    - Architecture creative: prose vs full make vs scripts vs hybrid
* Decisions made
    - **Option D Hybrid**: thin Makefile atoms (`localdev-clean`, optional local-plugin rsync helper, documented shim takeover) + narrative Contributing (`local-workflow.md` + slimmed `development.md`)
    - No silent mega `contrib-enter` target
* Insights
    - `make localdev` and `plugins/local` rsync are different surfaces; conflating them is a docs footgun

## 2026-07-12 - PLAN - COMPLETE

* Work completed
    - Full L3 plan in `tasks.md`: components, hybrid atoms implementation steps, Verification Plan (docs-build + manual Make checks M1–M3), challenges, pre-mortem
* Decisions made
    - Target names: `localdev-clean`, `plugin-local`, `make shim TAKEOVER=1`
    - New page `docs/contributing/local-workflow.md` owns Enter/Verify/Exit; development.md stays day-to-day
    - No new pytest files for Makefile (consistent with prior docs Verification Plan)
* Insights
    - Warehouse `aef4448b` is the golden Enter narrative; `bb1e3895` motivates `localdev-clean`

## 2026-07-12 - PREFLIGHT - COMPLETE

* Work completed
    - Validated plan against Makefile/docs reality; creative hybrid still fits
    - Amended TDD ordering for Make atoms; added `localdev-status` to plan
* Decisions made
    - Preflight PASS (with amendments applied in `tasks.md`)
* Insights
    - Docs Verification Plan alone is insufficient when Make targets are in scope — each atom needs check-before-implement encoding

## 2026-07-12 - BUILD - COMPLETE

* Work completed
    - Makefile: `localdev-clean`, `plugin-local`, `shim TAKEOVER=1`, `localdev-status`; torch comment → user-guide path
    - Docs: `local-workflow.md` owns Enter/Verify/Exit; development slimmed; CONTRIBUTING funnel + nav; troubleshooting links
    - Verified M1–M4, docs-build, reuse; skipped engine ci (no Python)
* Decisions made
    - No deviations from hybrid creative / plan
* Insights
    - `localdev-status` caught a pre-existing half-state (managed pre-commit block without skills-mirror) — Exit/status prose earns its keep

## 2026-07-12 - QA - COMPLETE

* Work completed
    - Semantic review vs plan + hybrid creative: completeness, no mega-target, SSOT split, docs/Makefile style
    - Trivial fix: Exit `sr-initialize` link aligned to quickstart (same as Enter)
* Decisions made
    - QA PASS; `.qa-validation-status` = PASS
* Insights
    - No substantive drift from hybrid decision — atoms stayed thin

## 2026-07-12 - REFLECT - COMPLETE

* Work completed
    - Wrote `memory-bank/active/reflection/reflection-contributing-localdev-guide.md`
    - Reconciled techContext + systemPatterns (local-workflow pointer; localdev ≠ plugin-local)
* Decisions made
    - productContext unchanged
* Insights
    - Preflight Make-check amendment was the highest-leverage process catch this run

## 2026-07-12 - REWORK INITIATED

* Operator chose rework (not archive) via `/niko build it!` after post-reflect design discussion.
* Rework feedback (locked design):
    - Doc story: full "rip it out" first (backup warehouse → uninstall plugin → stop dashboard → wire checkout), then modular "bits separately" appendix.
    - Always backup warehouse before enter (migration forward-compat risk).
    - Delete `plugin-local` entirely.
    - `make shim TAKEOVER=1 FORCE=1` — both flags required to claim a live foreign bake (deliberate two-key turn). FORCE is for localdev / recovering a broken install; downplayed elsewhere; not agent-default.
    - `make localdev` one-shot: local skills + local hooks (this project) + claim shim (TAKEOVER+FORCE) + bounce dashboard via `stockroom dashboard` (no new stop/restart subcommand).
    - Keep `localdev-clean` / `localdev-status`; status visually separates localdev-managed state from shim info.
    - Prerequisite: marketplace plugin uninstalled from harness so next launch uses project wiring.

## 2026-07-12 - COMPLEXITY-ANALYSIS - COMPLETE (rework)

* Work completed
    - Classified rework as Level 3
* Decisions made
    - Level 3 (not L2): FORCE alters succeed-or-refuse ownership policy; localdev grows hooks+shim claim; multi-surface docs rewrite
* Insights
    - Prior hybrid creative still useful history; FORCE + hooks-in-localdev supersede "takeover only for dead" and `plugin-local`

## 2026-07-12 - CREATIVE - COMPLETE (localdev-hooks-and-force)

* Work completed
    - Architecture creative for hooks + FORCE surface
* Decisions made
    - PATH-based project hooks (no PLUGIN_ROOT); FORCE+TAKEOVER for live; dead still TAKEOVER-only
* Insights
    - Cursor project hooks may be experiment-gated — localdev still bounces dashboard at enter

## 2026-07-12 - PLAN - COMPLETE (rework)

* Work completed
    - Full rework plan in tasks.md (S1–S5, M1–M4, docs B1–B3)
* Decisions made
    - Implementation order: shim FORCE → Makefile → docs → gates
* Insights
    - Claude hooks land in settings.local.json (gitignored); Cursor uses managed .cursor/hooks.json markers
