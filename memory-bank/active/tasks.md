# Task: polish-readme-sales-pitch

* Task ID: polish-readme-sales-pitch
* Complexity: Level 2
* Type: simple enhancement (docs / reader-facing)

Rewrite root `README.md` into a sales-forward GitHub first impression: pitch, product graphics, and published docs-site links (matching `CONTRIBUTING.md`), without redesigning the docs site.

## Test Plan (TDD)

### Behaviors to Verify

- [B1 Pitch]: Open `README.md` → first screenful conveys product identity (local faithful searchable warehouse) and a clear value pitch, not only a file index
- [B2 Graphics]: README embeds product screenshots from `docs/img/` (dashboard overview, conversation drill-in, and/or DuckDB CLI) with plain GitHub Markdown (no MkDocs `{ width=... }` attrs)
- [B3 Docs-site links]: Primary deep-dive links (quickstart, skills, architecture, contributing, licensing, advanced as used) resolve to `https://texarkanine.github.io/stockroom/...` URLs, not raw `docs/*.md` paths
- [B4 Quickstart accuracy]: Install + initialize steps match live quickstart (marketplace, Cursor third-party toggle note if kept brief, `/sr-initialize` vs `/stockroom:sr-initialize`, try `sr-search`)
- [B5 Skills table]: All five `sr-*` skills listed with correct roles; skill-index detail points at the docs site
- [B6 Licensing]: License section remains accurate (AGPL + PPL-S) and points at site licensing page (and/or `REUSE.toml` as secondary)
- [B7 No SSOT fork]: README does not invent a second user-guide corpus; it sells and routes — detail stays on the docs site / skills
- [B8 Image paths]: Relative image paths from repo root (`docs/img/...`) resolve in a GitHub blob view of `README.md`
- [Edge — empty pitch]: README without hero graphics or only bullet lists → fail B1/B2
- [Edge — relative docs links]: Reader-facing “go read X” links still pointing at `docs/...` → fail B3 (in-repo `CONTRIBUTING.md` / `REUSE.toml` pointers remain OK where GitHub convention expects them)

### Test Infrastructure

- Framework: none for README (docs-only surface). Same verification pattern as prior docs L2 tasks: acceptance checklist + targeted gate commands
- Test location: N/A (no pytest/js suite owns README)
- Conventions: verify against projectbrief acceptance criteria; run `make docs-build` only if `docs/` is touched (expected: not touched)
- New test files: none
- Verification commands at build end:
  1. Manual checklist B1–B8 against the written README
  2. Confirm image files exist at linked paths
  3. Spot-check docs-site URLs against `properdocs.yaml` `site_url` + known page paths
  4. `make docs-build` if any `docs/` change slips in; otherwise skip

## Implementation Plan

1. **Inventory graphics (no new assets expected)**
   - Files: `docs/img/stockroom-dashboard-top-light.png`, `docs/img/stockroom-dashboard-convo-light.png`, `docs/img/stockroom-duckdb-query.png`
   - Changes: Confirm reuse for README pitch. Do **not** request operator screenshots unless a chosen section has no suitable asset (current plan: reuse these three; skip `3rd-party-configs.png` in the sales surface — that belongs in quickstart)
2. **Rewrite `README.md` structure**
   - Files: `README.md`
   - Changes: Replace utilitarian index with ordered sections:
     1. Title + tagline
     2. Short sales pitch (aligned with `docs/index.md` / `productContext.md`, GitHub-flavored)
     3. Embedded graphics (dashboard → conversation → DuckDB offline query)
     4. Why stockroom (compact bullets)
     5. Quickstart (accurate, lean; link out to site quickstart for detail)
     6. Skills table + site skill-index link
     7. Documentation index (site URLs)
     8. License
3. **Retarget links to the published site**
   - Files: `README.md`
   - Changes: Prefer `https://texarkanine.github.io/stockroom/` paths with trailing slashes (same style as `CONTRIBUTING.md`). Keep marketplace / external tool links. Keep `CONTRIBUTING.md` as the GitHub contributing entry if useful, with site contributing underneath or instead for day-to-day docs
4. **Verify (checklist + path checks)**
   - Files: `README.md`, `docs/img/*` (read-only)
   - Changes: none beyond fixes found by B1–B8 checklist

## Technology Validation

No new technology - validation not required

## Dependencies

- Existing screenshots under `docs/img/`
- Published docs site base URL from `properdocs.yaml` (`https://texarkanine.github.io/stockroom/`)
- Pitch source of truth: `memory-bank/productContext.md` + `docs/index.md` (do not invent claims)

## Challenges & Mitigations

- **MkDocs image syntax on GitHub**: Docs use `{ width="400"}` attrs that GitHub ignores/breaks → Mitigation: plain `![alt](docs/img/....png)` only in README
- **Duplicating the docs homepage**: Risk of forking pitch SSOT → Mitigation: README sells + routes; deep narrative stays on the site; keep README shorter than `docs/index.md`
- **Stale relative `docs/` links**: Easy to leave some behind → Mitigation: B3 checklist pass before calling build done
- **Broken site paths**: Wrong MkDocs URL shape → Mitigation: mirror `CONTRIBUTING.md` trailing-slash style; cross-check against known pages under `docs/`

## Pre-Mortem

- **README becomes a second docs site**: Plan response — keep sections lean; every deep link goes to github.io; no new `docs/` pages in this task
- **Graphics don't show on GitHub**: already covered by Challenge (plain relative paths + B8)
- **Pitch overclaims product**: Plan response — stick to productContext / docs/index wording; no new capability claims

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Pre-Mortem complete
- [ ] Preflight
- [ ] Build
- [ ] QA
