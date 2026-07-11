# Task: release-quality-docs

* Task ID: release-quality-docs
* Complexity: Level 3
* Type: documentation / docs-site feature

Ship 1.0-quality documentation for Stockroom while remaining on major version 0: README funnel, CONTRIBUTING, restructured human `docs/` corpus, properdocs site + CI/Pages — per `memory-bank/active/creative/creative-release-quality-docs.md` Option A (lean skills + human site SSOT; dual-audience ≈ `system-model.md` only; snippets ≈ 0).

## Pinned Info

### Audience & ownership map

Why pinned: every implementation step must respect this partition; violating it recreates the rejected snippet-farm / SLOBAC-overfit plans.

```mermaid
graph TD
    classDef agent fill:#f3e5f5,stroke:#6a1b9a;
    classDef human fill:#e3f2fd,stroke:#1565c0;
    classDef maint fill:#fff8e1,stroke:#f9a825;

    K["SKILL.md operational how"]:::agent
    M["references/system-model.md using-agent why"]:::agent
    D["docs/ human site SSOT"]:::human
    SP["memory-bank/systemPatterns.md maintainer briefing"]:::maint

    K -.->|"do not fork flags into"| D
    M -.->|"doctrines rhyme; do not merge"| SP
    D -->|"Pages + GitHub"| H["Human readers"]
    K --> A["Plugin using-agent"]
    M --> A
    SP --> Dev["Maintaining agent / contributor"]
```

## Component Analysis

### Affected Components

- **README.md**: thin product landing → rewrite to what → pitch → quickstart → skills table → docs/contrib/license.
- **CONTRIBUTING.md** (new): contributor entry; ownership rule; system-model vs systemPatterns; pointers to contributor-guide.
- **docs/**: today `using.md`, `development.md`, `torch.md`, `img/` → restructure into user-guide / architecture / contributor-guide (+ advanced CLI, troubleshooting); migrate content; fix internal links.
- **properdocs toolchain** (new): root `pyproject.toml` stub + `[dependency-groups] docs`, `uv.lock`, `properdocs.yaml`, `.gitignore` `site/`, optional local `make docs` target.
- **CI / Pages** (new): docs build workflow (strict) + deploy on release/`workflow_dispatch` (sibling pattern).
- **skills/**: no user-guide corpus under `references/`; keep `system-model.md`; optional one-line guardrail cross-check only if a high-cost warning is missing — prefer not editing skills unless links in docs need accuracy.
- **memory-bank persistent**: no required content change; CONTRIBUTING cites systemPatterns vs system-model.

### Cross-Module Dependencies

- README → docs/user-guide + Pages URL (when known).
- CONTRIBUTING → docs/contributor-guide + systemPatterns + system-model (cite only).
- docs/architecture → link to `skills/sr-search/references/system-model.md` (GitHub-relative), not a snippet farm.
- docs/user-guide/install ← content from today's `docs/using.md`.
- docs/contributor-guide ← `development.md` / `torch.md`.
- properdocs build reads `docs/` + `properdocs.yaml`; CI installs via `uv sync --group docs --frozen`.
- Img assets: keep under `docs/img/` for install screenshots (human/site).

### Boundary Changes

- No Python engine API/schema changes.
- New public surfaces: GitHub Pages doc site; CONTRIBUTING; expanded docs URLs.
- Root gains a docs-only `pyproject.toml` (stub `[project]`, not a publishable package) — parallel to slobac/ai-rizz; does not replace `skills/sr-search/pyproject.toml`.

### Invariants & Constraints

- Must preserve skill-first usage; must not fork `SKILL.md` flag/init step lists into docs.
- Must preserve plugin packing: agents depend on skills + `system-model`, not Pages/`docs/`.
- Must preserve PPL-S carveout boundary (no dumping contributor AGPL-adjacent novels into `references/`).
- Must preserve dual-audience set ≈ `system-model.md` only; snippets ≈ 0.
- Must not document end-user `make`/`uv` bootstrap as alternate to `sr-initialize`.
- Must hold: `properdocs build --strict` clean; `reuse lint` still clean if REUSE.toml needs path updates.
- Non-goal: 1.0 product release / version bump for the sake of docs.

## Open Questions

- [x] Documentation corpus IA (what/where/ownership, skills vs site, snippets, advanced CLI, system-model vs systemPatterns) → Resolved: Option A lean skills + human site SSOT (see `memory-bank/active/creative/creative-release-quality-docs.md`).
- [x] Properdocs toolchain viability on this machine → Resolved in Plan tech validation: `properdocs==1.6.7` + Material + awesome-pages builds `--strict` in scratch PoC.

None remaining — implementation approach is clear.

## Test Plan (TDD)

### Behaviors to Verify

- **Strict site build**: `uv sync --group docs --frozen` + `uv run properdocs build --strict` → exit 0, no link/anchor warnings-as-errors.
- **Required corpus present**: after migration, paths exist: `docs/user-guide/{quickstart,install,using-skills,troubleshooting}.md`, `docs/user-guide/advanced/{index,cli}.md`, `docs/architecture/index.md`, `docs/contributor-guide/{development,torch,licensing}.md`, `docs/index.md`, `CONTRIBUTING.md`.
- **README funnel**: README contains sections/headings for product identity, quickstart, skills table, contributing/license pointers (content review + optional structural assert in a small docs hygiene test if we add one).
- **Ownership hygiene**: no new `skills/**/references/docs/` user-guide tree; `system-model.md` remains the sole shared using-agent doctrine file.
- **REUSE**: `make reuse` (or `reuse lint`) still passes after new files (annotate via REUSE.toml aggregates as needed).
- **Edge — relative links**: architecture page links to system-model resolve on GitHub and do not break strict build (use repo-relative or absolute github URLs consistent with sibling validation settings).
- **Edge — old paths**: remove or redirect stale `docs/using.md` etc. so nothing dangling; prefer delete-after-migrate over leaving stubs that confuse.

### Test Infrastructure

- Framework: **properdocs strict build** as primary docs gate (sibling pattern); Python **pytest** under `skills/sr-search/tests/` for any optional hygiene asserts; **reuse lint** via Makefile.
- Test location: CI workflow + optional `skills/sr-search/tests/test_docs_layout.py` (only if a lightweight path-existence test is worth it — prefer CI build alone unless packaging tests already set a precedent).
- Conventions: match slobac/ai-rizz docs CI (`uv sync --group docs --frozen`, `properdocs build --strict`).
- New test files: optional; default **none** beyond CI — docs content correctness is human/review + strict link check.

### Integration Tests

- CI docs workflow green on PR (build job).
- Manual: `uv run properdocs serve` smoke locally once during build.
- Operator handoff: GitHub Pages source = GitHub Actions after first deploy workflow (cannot be set by YAML alone).

## Implementation Plan

Authority: `memory-bank/active/creative/creative-release-quality-docs.md`.

1. **Docs toolchain scaffold**
    - Files: `pyproject.toml` (root stub), `properdocs.yaml`, `uv.lock` (via `uv lock`), `.gitignore` (`site/`, `.venv` already), optionally `Makefile` target `docs` / `docs-serve`.
    - Changes: dependency group `docs` matching slobac pins (properdocs, mkdocs-material, awesome-pages, pymdown-extensions); Material theme + strict validation + GitHub-compatible slugify; **no** panzoom unless needed; snippets enabled in config but unused by default.
    - Verify: `uv sync --group docs && uv run properdocs build --strict` against a minimal `docs/index.md` placeholder, then grow content.

2. **Restructure docs corpus (migrate, then write)**
    - Files: create `docs/user-guide/`, `docs/architecture/`, `docs/contributor-guide/`, `docs/user-guide/advanced/`; move `docs/img/`; delete obsolete top-level `using.md` / relocate `development.md` / `torch.md`.
    - Changes: substantive pages per creative tree; install content from `using.md`; contributor from development/torch; new troubleshooting + advanced CLI + using-skills + architecture + licensing + index + `.pages` nav.
    - Creative ref: ownership + advanced CLI + troubleshooting seed list.

3. **README + CONTRIBUTING**
    - Files: `README.md`, `CONTRIBUTING.md` (new).
    - Changes: funnel README; CONTRIBUTING with ownership rule, system-model vs systemPatterns, pointers to contributor-guide / make targets.

4. **CI / Pages**
    - Files: `.github/workflows/docs.yaml` (+ optional reusable build workflow mirrored from slobac, or inline single workflow); ensure `site_url` / `repo_url` in `properdocs.yaml` point at `Texarkanine/stockroom`.
    - Changes: PR build gate; deploy on release published + `workflow_dispatch`; document Pages Settings handoff in CONTRIBUTING or contributor-guide if needed.

5. **Licensing / hygiene**
    - Files: `REUSE.toml` if new paths need aggregate annotations; run `make reuse`.
    - Changes: ensure new markdown covered; no accidental PPL-S expansion into contributor docs.

6. **Final verification**
    - `uv run properdocs build --strict`
    - `make reuse` (and existing `make ci` if unaffected / still green)
    - Spot-check: no skill user-guide dump; system-model untouched unless a factual fix is required

## Technology Validation

**New technology:** properdocs docs toolchain at repo root (new to stockroom; established in ai-rizz/slobac).

**PoC (2026-07-11):** `/tmp/stockroom-docs-poc` with `properdocs ~= 1.6`, Material, awesome-pages, pymdown-extensions → `uv sync --group docs` + `uv run properdocs build --strict` → **PASS** (`properdocs==1.6.7`).

No other new runtime dependencies.

## Challenges & Mitigations

- **Strict build fails on links to `../skills/.../system-model.md`:** use absolute `https://github.com/Texarkanine/stockroom/blob/main/skills/...` or keep architecture self-contained with a short paraphrase + “canonical for agents: path in repo” without a fragile relative link; validate during step 2.
- **Root `pyproject.toml` confuses contributors into thinking the engine moved:** comment stub clearly (slobac style); point engine at `skills/sr-search/` in CONTRIBUTING and techContext if we touch it.
- **Content drift from skills:** ownership rule in CONTRIBUTING; do not copy flag tables; review against `SKILL.md` during QA.
- **Pages not live until Settings click:** document operator handoff; README can link to `docs/` on GitHub until Pages URL works.
- **REUSE annotations for many new files:** prefer REUSE.toml path aggregates over per-file headers.

## Pre-Mortem

- **Plan failed because we rebuilt the snippet-farm / put user-guide under `references/`:** already constrained by creative Option A and invariants — treat as hard fail in preflight/QA if violated.
- **Plan failed because docs are beautiful but friends still can't install:** mitigate by prioritizing accurate install + troubleshooting + README quickstart in step 2/3 ordering (write those before architecture niceties).
- **Plan failed because root docs pyproject / lock fights engine uv workflow:** already covered by Challenge (clear stub comments; separate lock at root is fine — engine keeps its own lock under `skills/sr-search/`).

## Status

- [x] Component analysis complete
- [x] Open questions resolved
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Pre-Mortem complete
- [ ] Preflight
- [ ] Build
- [ ] QA
