# Project Brief

## User Story

As Stockroom's maintainer (and early adopters' first landing surface), I want 1.0-quality documentation — README funnel, CONTRIBUTING, properdocs site, and a real `docs/` corpus — so that friends and coworkers can install and use the product while I solicit feedback, and so the project's mental model stays clear without waiting for a 1.0 code release.

## Use-Case(s)

### Use-Case 1 — Early adopter lands

A friend or coworker installs from the marketplace, follows README → quickstart/install, runs `sr-initialize`, and knows to ask the agent or slash-invoke skills; if something fails, human troubleshooting on the doc site helps them recover.

### Use-Case 2 — Power user without another chat turn

After setup, a human uses `stockroom query` / `semantic` (and optionally the DuckDB CLI) per the advanced CLI docs, without further agentic inference.

### Use-Case 3 — Contributor orients

A contributor reads CONTRIBUTING → contributor-guide (Makefile, torch contract, licensing) and understands how maintainer briefing (`systemPatterns.md`) differs from using-agent doctrine (`system-model.md`).

### Use-Case 4 — Maintainer keeps the map

The doc IA matches the creative decision so future feedback has an obvious file to land in, without forking skill operational docs into a second manual.

## Requirements

1. Rewrite README as what → pitch → quickstart → skills table → docs/contrib/license pointers.
2. Add CONTRIBUTING.md for non-obvious contribution (torch, engine-under-skill, REUSE, dual manifests); point at contributor-guide and note system-model vs systemPatterns.
3. Restructure/expand `docs/` into real pages: user-guide (quickstart, install, using-skills, troubleshooting, advanced CLI), architecture (human tour; link to system-model), contributor-guide (development, torch, licensing).
4. Add properdocs (Material, strict validation) + docs dependency group + CI/Pages publish path matching sibling repos.
5. Keep skills lean: no user-guide corpus under `references/`; keep `system-model.md`; no snippet farm (snippets ≈ 0).
6. Do not document end-user bootstrap via `make`/`uv` as an alternative to `sr-initialize`.

## Constraints

1. Execute `memory-bank/active/creative/creative-release-quality-docs.md` (Option A — lean skills + human site SSOT); do not reopen settled IA without evidence.
2. Plugin agents must not depend on Pages or repo-root `docs/`; dual-audience ≈ `system-model.md` only.
3. PPL-S carveout stays on skill prompt payload; contributor docs stay outside it.
4. Prefer zero pymdownx snippets; at most one for system-model if a link is insufficient.
5. Not a 1.0 product release — docs quality only while remaining on major version 0.
6. Minimize duplication with `SKILL.md` operational content (link/point, don't fork flag tables).

## Acceptance Criteria

1. README matches the funnel shape and links to the doc site (or `docs/` until Pages is live).
2. CONTRIBUTING.md exists and routes contributors correctly.
3. `docs/` tree matches the creative layout with substantive content for install, using-skills, troubleshooting, advanced CLI, architecture, contributor-guide.
4. `properdocs build --strict` succeeds; CI gates docs; Pages deploy path is in place (or documented operator handoff if Settings require a manual click).
5. Skills and `system-model.md` are not bloated with human user-guide prose; ownership rule is stated in CONTRIBUTING.
6. Creative decision document remains the IA authority; no competing "docs in references/docs/" tree.
