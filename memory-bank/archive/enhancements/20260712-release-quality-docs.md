---
task_id: release-quality-docs
complexity_level: 3
date: 2026-07-12
status: completed
---

# TASK ARCHIVE: release-quality-docs

## SUMMARY

Shipped Option A release-quality human docs for Stockroom (properdocs site, README funnel, CONTRIBUTING, `docs/` corpus) while staying on major version 0, then iterated six L2 review reworks until the **user guide** met operator acceptance (`chore: User guide is done!`).

**Acceptance boundary at archive:** the user-guide tree is reviewed and accepted. Advanced, Architecture, and Contributing retain scaffolding/substantive drafts from the original L3 build but were **not** fully reviewed or accepted in this run — follow-up work should be separate tasks, not further reworks on this id.

## REQUIREMENTS

Original (L3):

1. README funnel: what → pitch → quickstart → skills → docs/contrib/license.
2. CONTRIBUTING for non-obvious contribution (torch, engine-under-skill, REUSE, dual manifests); system-model vs systemPatterns ownership.
3. `docs/` per creative Option A: user-guide, architecture (human tour), contributor-guide; lean skills (no `references/docs/` dump); snippets ≈ 0.
4. properdocs + docs dependency group + CI/Pages; agents must not depend on Pages.
5. No end-user bootstrap via `make`/`uv` as alternative to `sr-initialize`.

Review reworks (L2 chain): Quickstart vs Installed layout; torch → user-guide; ingest / search / dashboard drafts; alphabetical skill index; troubleshooting heading deep-links; user-guide index mental model + sequence diagrams.

## IMPLEMENTATION

### Creative (Option A — inlined)

Lean skills + human site SSOT. Dual-audience ≈ `system-model.md` only. Human install/troubleshoot/CLI/architecture/contributor prose lives under `docs/` (properdocs). Do not merge system-model (using-agent doctrine) with `systemPatterns.md` (maintainer briefing). Prefer links over pymdownx snippets.

### Phases

1. **L3 build** — root docs toolchain (properdocs 1.6.7), full Option A tree, README + CONTRIBUTING, Pages workflow; docs-build + reuse + engine suite green; QA PASS (Pages Settings handoff).
2. **Rework 1** — Quickstart owns get-running ritual; Installed layout owns on-disk topology; local/dev → contributing; `contributor-guide` → `contributing` link cascade.
3. **Rework 2** — Operator torch SSOT at `user-guide` (later `troubleshooting/torch.md`); deleted contributing torch page; fold `make torch` into `development.md`.
4. **Rework 3–4** — Finished `ingest.md`, `search.md`, `dashboard.md`; slim discovery pages when depth pages land.
5. **Rework 5–6** — Alphabetical skill index; troubleshooting heading-per-symptom catalog (nav-ordered); torch remedies as headings on torch page only.
6. **Post-reflect** — User-guide `index.md` Install once / Use it / Stay fresh + sequence diagrams.

### Key surfaces

| Area | Paths |
| --- | --- |
| Toolchain | root `pyproject.toml`, `uv.lock`, `properdocs.yaml`, `.github/workflows/docs.yaml`, `Makefile` docs targets |
| Funnel | `README.md`, `CONTRIBUTING.md` |
| User guide (accepted) | `docs/user-guide/**` including troubleshooting |
| Other sections (not fully accepted) | `docs/advanced/**`, `docs/architecture/**`, `docs/contributing/**` |
| Persistent reconcile | `memory-bank/systemPatterns.md`, `memory-bank/techContext.md` (docs ownership / properdocs pointers) |

## TESTING

- Gates throughout: `make docs-build` (properdocs `--strict`), `make reuse`; engine suite stayed green after soft-fail path hygiene in original build.
- `/niko-qa` PASS on original L3 and each rework (trivial fixes only when needed: Pages handoff, README local/dev over-claim, incremental-before-`--full` on ingest staleness).
- No pytest theater for markdown — Verification Plan (docs-only) per preflight.

## LESSONS LEARNED

- After renaming a docs section or moving a page into a subdirectory, audit *relative* inbound/outbound links in the same change — preview can look fine while properdocs `--strict` fails.
- Audience mis-home is a recurring smell when one page mixes marketplace heal remedies with `make` recipes — split early (torch).
- Discovery pages (`skills` / former using-skills) must be slimmed in the same change as depth pages or they become competing SSOTs.
- Material slugifies `/` in headings to `--`; verify generated anchors under strict build.
- Quickstart (ritual) vs Installed layout (topology) should have been two jobs in the first creative.
- Docs-only L3 wants Verification Plan gates, not invented layout pytest; operator handoffs need checklist checkboxes or they slip until QA.

## PROCESS IMPROVEMENTS

- Multiple L2 reworks on one task id before archive is fine when review drives polish; progress history preserves the chain — but close when the accepted slice is done rather than forever-extending.
- Treat operator WIP on the same branch as the verification base when it already contains in-progress IA moves.

## TECHNICAL IMPROVEMENTS

- Root docs `uv.lock` coexists cleanly with engine `skills/sr-search/uv.lock` when Makefile targets keep them separate.
- GitHub-absolute links for system-model / Makefile / skills avoid fragile out-of-`docs_dir` relatives.

## NEXT STEPS

1. Separate `/niko` runs to bring **Advanced**, **Architecture**, and **Contributing** to the same reviewed quality bar as the user guide (do not reopen this task id).
2. Unrelated leftover preserved in active: `memory-bank/active/creative/creative-embedding-invalidation.md` (embedding invalidation on ingest — not part of this task). Decide whether to start that work or park/delete it deliberately.
