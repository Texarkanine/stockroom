# Progress

Rework 3 of release-quality-docs: draft `docs/user-guide/ingest.md` (ingest / embed / scheduling) to finished user-guide quality, matching Quickstart / Installed layout / Torch troubleshooting style. Prior IA + torch reworks remain.

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

## 2026-07-12 - BUILD - COMPLETE

* Work completed
    - Quickstart / Installed layout split; local/dev → contributing; link cascade; docs-build + reuse green
* Decisions made
    - Discovery link from Quickstart to Installed layout OK; ritual not deferred
* Insights
    - WIP `contributing/` / `advanced/` moves left relative links that only fail under properdocs strict

## 2026-07-12 - QA - COMPLETE

* Work completed
    - Semantic review against rework brief; trivial README wording fix; docs-build re-PASS
    - `.qa-validation-status` = PASS
* Decisions made
    - No substantive rework required
* Insights
    - README blurb can over-claim “local/dev” after content moves to contributor guide

## 2026-07-12 - REFLECT - COMPLETE

* Work completed
    - Wrote `memory-bank/active/reflection/reflection-release-quality-docs-rework.md`
    - Persistent reconcile: no further edits (contributing paths already fixed in build)
* Decisions made
    - Keep original L3 reflection alongside rework reflection
* Insights
    - Relative link fallout after docs section renames is the recurring lesson

## 2026-07-12 - REWORK 2 INITIATED

* Trigger: review feedback — torch docs belong in user-guide, not contributing-only
* Feedback / agreed direction:
    - Create `docs/user-guide/torch.md` as operator SSOT (why out of lock, smoke→freeze, heal, artifacts, failure remedies)
    - Shrink/remove `docs/contributing/torch.md` to contributor-only (`make torch`, manual freeze, shared deps) or fold into development.md
    - Troubleshooting + Installed layout + CONTRIBUTING + skill links retarget
    - Architecture at most a pointer; not Advanced-owned

## 2026-07-12 - COMPLEXITY-ANALYSIS - COMPLETE (rework 2)

* Work completed
    - Classified rework 2 as Level 2 (docs page move + link cascade; settled IA)
* Decisions made
    - Same level as prior IA rework; not L3 (no toolchain / corpus reopen)
* Insights
    - Second rework on same task id before archive is fine; progress history preserves both

## 2026-07-12 - PLAN - COMPLETE (rework 2)

* Work completed
    - Plan: user-guide/torch.md SSOT; delete contributing/torch.md; fold make-torch into development.md; link cascade; docs-build
* Decisions made
    - Prefer delete contributing torch page over thin zombie duplicate
* Insights
    - Operator Installed layout WIP is base; torch links are surgical

## 2026-07-12 - PREFLIGHT - COMPLETE (rework 2)

* Work completed
    - PASS; Verification Plan amendment; prefer delete contributing/torch
* Decisions made
    - Docs-only TDD N/A
* Insights
    - None beyond plan

## 2026-07-12 - BUILD - COMPLETE (rework 2)

* Work completed
    - user-guide/torch.md; deleted contributing/torch.md; development.md contributor bits; link cascade; docs-build + reuse green
* Decisions made
    - User-guide owns contract + failure table; development owns make torch / manual freeze / shared deps
* Insights
    - Installed layout torch rows now deep-link to Torch page

## 2026-07-12 - QA - COMPLETE (rework 2)

* Work completed
    - Semantic review PASS; no fixes
* Decisions made
    - Skip architecture one-liner (YAGNI)
* Insights
    - None

## 2026-07-12 - REFLECT - COMPLETE (rework 2)

* Work completed
    - Wrote `reflection-release-quality-docs-torch.md`
* Decisions made
    - Ready for archive (third reflect on this task id)
* Insights
    - Audience mis-home for mixed make/heal docs is a recurring smell

## 2026-07-12 - REWORK 3 INITIATED

* Trigger: continuation of docs polish — fill stub user-guide pages with solid drafts
* Feedback / agreed direction:
    - Draft `docs/user-guide/ingest.md` as a finished-quality user-guide page (replace todo placeholders)
    - Match style/vibes of finished examples: `quickstart.md`, `installed-layout.md`, `troubleshooting/torch.md`
    - Page already stubs Ingest / Embed / Scheduling sections; flesh those out from product behavior (`sr-initialize`, CLI, nightly schedule)

## 2026-07-12 - COMPLEXITY-ANALYSIS - COMPLETE (rework 3)

* Work completed
    - Classified rework 3 as Level 2 (simple enhancement): one user-guide page draft + light link DRY; style/IA already exemplified by finished pages
* Decisions made
    - Level 2 — not L1 (substantive content, not a typo); not L3 (no toolchain, no multi-section corpus redesign)
* Insights
    - Filling stub pages against settled style examples is the same shape as prior IA reworks on this task id

## 2026-07-12 - PLAN - COMPLETE (rework 3)

* Work completed
    - Implementation plan: draft ingest.md → reconcile WIP torch/troubleshooting links for strict build → verify
    - Behaviors B1–B5 + edge cases E1–E3
* Decisions made
    - User-guide owns mental model; Advanced CLI owns flag escape hatch; do not reverse operator torch→troubleshooting WIP
    - Docs gates only (no pytest)
* Insights
    - Operator WIP already moved torch under troubleshooting/; plan must retarget broken inbound links or verification cannot pass

## 2026-07-12 - PREFLIGHT - COMPLETE (rework 3)

* Work completed
    - Validated plan against docs-only conventions; `.preflight-status` = PASS
    - Amended Verification Plan wording + optional coverage-query one-liner in draft step
* Decisions made
    - TDD N/A (same as prior docs reworks); do not reverse torch→troubleshooting WIP
* Insights
    - Strict build cannot validate ingest until WIP inbound torch/troubleshooting links match on-disk paths

## 2026-07-12 - BUILD - COMPLETE (rework 3)

* Work completed
    - Drafted `docs/user-guide/ingest.md`; reconciled WIP torch/troubleshooting links; stub H1s for search/dashboard
    - `make docs-build` PASS; `make reuse` PASS; acceptance B1–B5
* Decisions made
    - Also retargeted CONTRIBUTING / systemPatterns / techContext / sr-initialize torch paths (outside properdocs but broken after WIP move)
* Insights
    - Moving a page into a subdirectory silently breaks sibling-relative links in the old parent file

## 2026-07-12 - QA - COMPLETE (rework 3)

* Work completed
    - Semantic review against Rework 3 brief; trivial fix: incremental catch-up before `--full` for staleness
    - docs-build re-PASS; `.qa-validation-status` = PASS
* Decisions made
    - No substantive rework required
* Insights
    - “Same as initialize” is easy to over-apply to the everyday stale path
