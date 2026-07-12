# Progress

Rework of release-quality-docs: split Quickstart (self-contained get-running) from Installed layout (what landed where); move local/dev plugin load to contributor docs; fix nav/inbound links. Original Level 3 docs ship remains; this delta is review feedback.

**Complexity:** Level 2

## 2026-07-11 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - Validated intent: full docs creative now (not thin-slice deferral)
    - Classified Level 3 (multi-component docs feature; creative IA already done)
    - Created ephemeral memory-bank files (projectbrief, activeContext, tasks stub, progress)
* Decisions made
    - Scope = full Option A creative plan, not thin-slice-only
    - Stay on 0.x product version; docs quality is the deliverable
* Insights
    - Early-adopter week still benefits from full docs because maintainer wants the map; feedback can land in an already-rigorous corpus

## 2026-07-11 - PLAN - COMPLETE

* Work completed
    - Component analysis across README, CONTRIBUTING, docs/, properdocs toolchain, CI/Pages
    - Implementation plan: 6 ordered steps (toolchain → corpus → README/CONTRIBUTING → CI → REUSE → verify)
    - Technology validation PoC for properdocs at `/tmp/stockroom-docs-poc` — PASS
* Decisions made
    - Match slobac docs dependency set (no panzoom unless needed)
    - Root stub `pyproject.toml` for docs group only; engine lock stays under `skills/sr-search/`
    - Prefer GitHub absolute or careful links to system-model over snippet farm
* Insights
    - Prior creative already removed the hard IA ambiguity; plan phase was sequencing + toolchain proof

## 2026-07-11 - PREFLIGHT - COMPLETE

* Work completed
    - Validated conventions, completeness, dependency impact
    - Amended plan: Verification Plan (properdocs strict + reuse + ownership review) instead of code TDD theater
    - `.preflight-status` = PASS
* Decisions made
    - Docs-only task → no pytest layout tests; gates are build/reuse/QA review
* Insights
    - Operator pushback was correct: inventing “tests” for markdown would only create busywork

## 2026-07-11 - BUILD - COMPLETE

* Work completed
    - Docs toolchain at repo root (properdocs 1.6.7, Material, awesome-pages)
    - Full Option A corpus under `docs/`; README + CONTRIBUTING; Pages workflow
    - Path hygiene for moved torch/dev docs; reuse + strict build + full engine suite green
* Decisions made
    - GitHub absolute links for system-model / Makefile / skills (no fragile out-of-`docs_dir` relatives)
    - Single docs workflow for PR gate + deploy (no reusable workflow split — stockroom is simpler than ai-rizz)
    - Snippets enabled in config but unused (snippets ≈ 0)
* Insights
    - Root docs `uv.lock` coexists cleanly with engine lock under `skills/sr-search/`

## 2026-07-11 - QA - COMPLETE

* Work completed
    - Semantic review against Option A + acceptance criteria
    - Trivial fix: Pages Settings handoff documented in contributor-guide
    - `.qa-validation-status` = PASS
* Decisions made
    - No substantive rework required
* Insights
    - Plan called out Pages handoff explicitly; easy to miss in a docs-only build without QA checklist

## 2026-07-11 - REFLECT - COMPLETE

* Work completed
    - Wrote `memory-bank/active/reflection/reflection-release-quality-docs.md`
    - Reconciled techContext (properdocs / docs CI) and systemPatterns (docs ownership)
* Decisions made
    - productContext unchanged (docs polish does not change product picture)
* Insights
    - Docs-only Level 3 wants verification gates, not pytest theater; operator handoffs need checklist boxes

## 2026-07-12 - REWORK INITIATED

* Trigger: PR/review feedback during docs review — operator chose rework over archive
* Feedback (from `/nk-chat` review of `docs/user-guide/quickstart.md` + `install.md`):
    - Quickstart and Install duplicate the marketplace → `sr-initialize` path; Quickstart currently defers to Install instead of being self-contained
    - Operator does not want Quickstart sending readers to external harness docs for the happy path; outbound marketplace how-to may link to https://github.com/Texarkanine/txrk9-agent-plugins (that README owns marketplace add)
    - Install's distinctive value is "what landed where" (layout / on-disk topology), not a second install ritual — "Install" is the wrong name
    - Preferred direction from chat: rename toward **Installed layout**; Quickstart owns the get-running ritual (marketplace + Cursor third-party toggle screenshot + `sr-initialize` + first try); layout page owns dual-manifest/skills tree, runtime home (XDG/`STOCKROOM_HOME`, shim, torch freeze, schedule), plugin≠marketplace gotcha
    - Local/dev plugin load (`rsync` / `--plugin-dir`) fits contributor-guide better than the post-install layout page
    - Cascade: `.pages`, README, troubleshooting, using-skills, contributing/torch inbound links

## 2026-07-12 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - Classified rework as Level 2 (simple enhancement): self-contained docs IA fix across user-guide pages + link cascade; design settled in chat; does not reopen Option A corpus architecture
* Decisions made
    - Level 2 — not L1 (multi-file rename + content ownership change, not a typo/link fix); not L3 (no new subsystem / docs toolchain)
* Insights
    - Review-time IA splits are often L2 even when the original task was L3

## 2026-07-12 - PLAN - COMPLETE

* Work completed
    - Implementation plan: rewrite Quickstart → create `installed-layout.md` → move local/dev to `docs/contributing/development.md` → link cascade → properdocs strict
    - Behaviors B1–B7 + edge cases for WIP `contributor-guide` → `contributing` breakage
* Decisions made
    - Docs gates only (no pytest); do not reopen Option A or redesign using-skills vs ingest/search/dashboard in this rework
* Insights
    - Review WIP already renamed contributor-guide; rework link cascade must repair README/CONTRIBUTING or strict build / readers break

## 2026-07-12 - PREFLIGHT - COMPLETE

* Work completed
    - Validated plan against docs-only conventions; amended Verification Plan + explicit Installed layout nav title
    - `.preflight-status` = PASS
* Decisions made
    - TDD N/A (same as original docs task); do not redesign using-skills IA in this rework
* Insights
    - Review WIP path rename is a latent acceptance failure until link cascade runs
