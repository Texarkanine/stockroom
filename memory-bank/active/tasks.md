# Task: release-quality-docs

* Task ID: release-quality-docs
* Complexity: Level 2
* Type: documentation IA rework (simple enhancement)

Split Quickstart vs Installed layout per `projectbrief.md` Rework: self-contained get-running ritual; retarget `install.md` → `installed-layout.md` (what landed where); move local/dev plugin load into `docs/contributing/development.md`; update nav and inbound links. Base tree already includes review WIP (`docs/contributing/`, expanded user-guide pages).

## Test Plan (TDD)

Docs-only rework — no production code under test. Do **not** invent pytest theater. Gates below are the verification plan.

### Behaviors to Verify

- **B1 Quickstart self-contained**: Reader following only `docs/user-guide/quickstart.md` can add the marketplace, install `stockroom`, enable the Cursor third-party toggle (screenshot present), run `sr-initialize`, and know a first try — without opening Installed layout.
- **B2 No ritual deferral**: Quickstart does not say “details: Install/Installed layout” for the happy path; marketplace-add may link only to https://github.com/Texarkanine/txrk9-agent-plugins.
- **B3 Layout page job**: `installed-layout.md` covers dual-manifest / shared `skills/`, runtime home (`STOCKROOM_HOME` / XDG, shim, torch freeze, schedule), and plugin≠marketplace gotcha — not a second click-by-click marketplace procedure.
- **B4 DRY `sr-initialize`**: Full what-it-does paragraph lives once on Quickstart; layout page may mention on-disk outcomes only.
- **B5 Local/dev moved**: `rsync` / `claude --plugin-dir` live under `docs/contributing/development.md`; layout page has at most a pointer.
- **B6 Links**: No remaining references to `docs/user-guide/install.md` or stale `contributor-guide/` paths in README, CONTRIBUTING, docs, or nav; troubleshooting / using-skills point at the new page where appropriate.
- **B7 Build gate**: `uv run properdocs build --strict` (or `make docs-build`) PASS.

### Edge cases

- **E1 Broken WIP links**: `CONTRIBUTING.md` / README still cite `docs/contributor-guide/` after the rename to `docs/contributing/` — must be fixed as part of link cascade or strict build fails / acceptance fails.
- **E2 Orphan `using-skills.md`**: Still on disk and linked from README; out of rework *content* scope, but any Install→layout link inside it must be updated.
- **E3 Image path**: Third-party toggle screenshot must remain reachable from Quickstart (`docs/img/3rd-party-configs.png` or current relative path after site img layout).

### Test Infrastructure

- Framework: properdocs strict build (docs CI / `make docs-build`); `make reuse` if new paths need REUSE aggregates
- Test location: N/A for prose — gates are build/link integrity
- Conventions: same as original release-quality-docs verification plan
- New test files: none

## Implementation Plan

1. **Rewrite Quickstart (ritual owner)**
   - Files: `docs/user-guide/quickstart.md`
   - Changes: Self-contained steps — (1) add marketplace via link to [txrk9-agent-plugins](https://github.com/Texarkanine/txrk9-agent-plugins) + install `stockroom` (short Cursor/Claude slash forms inline, no harness-doc deep links required for happy path), (2) Cursor third-party toggle + move screenshot here from install, (3) `sr-initialize` with the single what-it-does paragraph, (4) first try / what next. Remove “details: Install” deferral.

2. **Create Installed layout; remove Install**
   - Files: add `docs/user-guide/installed-layout.md`; delete `docs/user-guide/install.md`; update `docs/user-guide/.pages` (`install.md` → `installed-layout.md`, title from filename or explicit “Installed layout”)
   - Changes: Content = committed layout = install layout; dual manifests + shared `skills/`; runtime home / shim / freeze / schedule; plugin≠marketplace; pointer to Quickstart for the ritual; pointer to contributing for local/dev load. No marketplace click matrix.

3. **Move local/dev plugin load to contributor docs**
   - Files: `docs/contributing/development.md` (new section); strip from former install content
   - Changes: Cursor `rsync` into `~/.cursor/plugins/local/stockroom/` + Claude `--plugin-dir`; keep “not end-user path” framing; fix any torch cross-links.

4. **Link + pointer cascade**
   - Files: `README.md`, `CONTRIBUTING.md`, `docs/user-guide/troubleshooting.md`, `docs/user-guide/using-skills.md`, `docs/contributing/torch.md`, any other `install.md` / `contributor-guide` refs under `docs/`
   - Changes: Install → Installed layout; `contributor-guide` → `contributing`; README quickstart blurb points at Quickstart for ritual, Installed layout only for layout/local-dev as needed.

5. **Verify gates**
   - Files: none (run commands)
   - Changes: `make docs-build` (or `uv run properdocs build --strict`); `make reuse` if path aggregates need a glance; spot-check Quickstart alone satisfies B1–B2.

## Technology Validation

No new technology - validation not required

## Dependencies

- Existing review WIP on branch: `docs/contributing/` rename, user-guide nav expansion, img assets — treat as base tree; do not revert.
- Screenshot asset `docs/img/3rd-party-configs.png` (or path used by current install.md).
- Marketplace README at https://github.com/Texarkanine/txrk9-agent-plugins remains the how-to for adding a marketplace.

## Challenges & Mitigations

- **Quickstart grows too long if we paste full Cursor+Claude click paths**: Keep steps short; defer marketplace-*add* UI detail to txrk9-agent-plugins README; keep only stockroom-specific bits (plugin name, slash forms, third-party toggle) inline.
- **WIP left CONTRIBUTING/README on old `contributor-guide` paths**: Fix in step 4; strict build / manual link sweep catches leftovers.
- **`using-skills.md` vs new ingest/search/dashboard pages**: Do not redesign that IA in this rework; only fix Install links inside using-skills.
- **Persistent memory-bank still cites `docs/contributor-guide/`**: Out of product docs gate; optional one-line fix in techContext/systemPatterns only if we already touch path hygiene — prefer not expanding scope; note for reflect.

## Pre-Mortem

- **Plan failed because Quickstart still links out to Cursor/Claude plugin docs and feels incomplete without Install**: Cut those links from the happy path; txrk9-agent-plugins + inline stockroom steps only (Challenge 1).
- **Plan failed because “Installed layout” became a second install guide under a new name**: Acceptance B3/B4 — strip marketplace procedure in step 2 review before gates.
- **Plan failed because local/dev content was deleted instead of moved**: Step 3 explicitly migrates to `development.md` before deleting from layout page.

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Pre-Mortem complete
- [ ] Preflight
- [ ] Build
- [ ] QA
