# Task: Load section information architecture

* Task ID: load-section-ia
* Complexity: Level 2
* Type: simple enhancement (docs)

Turn `docs/user-guide/load/index.md` into a section router; relocate the orphaned **Harness-Specific Notes** block by splitting it — generic ingest content back into `basic.md`, genuinely per-harness reference into a new `sources.md`; add the missing `load/.pages`; and repair the inbound-link fallout that currently makes the strict docs build red. No engine or CLI changes.

## Test Plan (TDD)

Docs-only work: no pytest behaviors. The test runner is `make docs-build` (`properdocs build --strict`), which fails the build on unresolvable links and anchors. Behaviors not mechanically checkable by the build are verified against a content checklist.

### Behaviors to Verify

- **B1** (`load/index.md` is a router): read the page → H1, one-sentence purpose, the two catch-up commands, and a named map of all four children (`basic`, `schedule`, `sources`, `backfill`). No prose sections beyond the map; whole page fits one viewport (~30 lines).
- **B2** (`load/sources.md` holds only per-harness reference): read the page → default transcript roots, the three `STOCKROOM_*_ROOT` overrides, Cursor Agent CLI chats best-effort parsing, and Cursor `sessions.models` enrichment (discovery walk, additive `[cursor].ai_tracking_dbs` pins, `STOCKROOM_AI_TRACKING_DB`). Nothing generic.
- **B3** (`load/basic.md` holds the generic chunks): read the page → `ingest` / `--full` / `--verbose` block, `--harness cursor|claude` flag, and the `sr-initialize` first-full-load timing note are present under `## Ingest`; no `## Scheduling` section; no harness-specific content.
- **B4** (nav order): `load/.pages` exists → section opens on `index.md` and lists `backfill` last.
- **B5** (anchor survival): build resolves `installed-layout.md` → `load/sources.md#cursor-sessionsmodels-enrichment`.
- **B6** (anchor retarget): build resolves `load/backfill/index.md` and `load/backfill/cursor-vscdb.md` `#ingest` links against `basic.md`, not the router.
- **B7** (green build): `make docs-build` exits 0 with **zero** warnings.

### Fail-First Baseline (captured 2026-07-26)

`make docs-build` → `Aborted with 38 warnings in strict mode!`, exit 2. The warnings are **two independent breakages**:

| Group | Cause | Count | In original rework scope? |
| --- | --- | --- | --- |
| A | `user-guide/ingest/` → `user-guide/load/` rename | 19 | Yes |
| B | `contributing/iteration.md` → `contributing/iteration/` nest | 19 | **No — discovered by the baseline** |

Group B is a separate earlier restructure by the operator, unrelated to the load section. It is pulled into scope because acceptance criterion 5 (zero-warning strict build) is unreachable without it, and the fix is the same mechanical class of edit.

### Edge Cases

- The `#cursor-sessionsmodels-enrichment` slug is consumed by `installed-layout.md` and was already broken once by a heading demotion in a prior build. Slug derives from heading *text*, not level — the text `Cursor \`sessions.models\` Enrichment` must survive the move verbatim.
- `../index.md#ingest` (both backfill pages) currently targets the router, which will have no `## Ingest`. Must retarget to `../basic.md#ingest`.
- `troubleshooting/index.md` `#scheduling` anchor: `schedule.md` is now its own page with that H1, so the link becomes a plain page link with no anchor.
- Backfill page bodies shipped in the prior rework — edit link targets only, no prose rewrites.
- Depth errors inside `contributing/iteration/`: sibling links (`preparation.md`) need `../`, cross-tree links (`../user-guide/…`, `../architecture/…`) need `../../`.

### Test Infrastructure

- Framework: ProperDocs / MkDocs strict build — `make docs-build` (`Makefile:88`)
- Test location: n/a (no pytest); run from repo root
- Conventions: human docs under `docs/`; agents do not consume them (`systemPatterns.md` → Docs ownership). Strict mode rejects directory-trailing-slash links — always link explicit `index.md`.
- New test files: none

## Implementation Plan

1. **Record fail-first baseline**
   - Files: none (read-only)
   - Changes: `make docs-build` → confirm 38 warnings and that B1–B7 all currently fail. **Done — table above.**
   - Verify: baseline recorded

2. **Split the Harness-Specific Notes block**
   - Files: `docs/user-guide/load/index.md`, `docs/user-guide/load/sources.md` (new), `docs/user-guide/load/basic.md`
   - Changes:
     1. Create `sources.md` — H1 "Sources", short lede, then `## Cursor` with best-effort chats parsing, transcript roots + the three env overrides, and `## Cursor \`sessions.models\` Enrichment` (verbatim heading text) with the discovery walk, `config.toml` pins, and `STOCKROOM_AI_TRACKING_DB`. Add `## Claude Code` for its root/default.
     2. Move the generic `ingest` command block, `--harness` flag, and `sr-initialize` first-load note into `basic.md` under `## Ingest`.
     3. Replace `index.md` body wholesale with the router.
   - Verify: B1, B2, B3

3. **Add section nav**
   - Files: `docs/user-guide/load/.pages` (new)
   - Changes: `nav:` → `index.md`, `Ingest & Embed: basic.md`, `Scheduling: schedule.md`, `Sources: sources.md`, `backfill`
   - Verify: B4

4. **Repair group A links (`ingest/` → `load/`)**
   - Files: `docs/user-guide/index.md`, `dashboard.md`, `search.md`, `skills.md`, `installed-layout.md`, `troubleshooting/index.md`, `load/backfill/index.md`, `load/backfill/cursor-vscdb.md`, `docs/architecture/{backfill,embeddings,lifecycle,warehouse}.md`, `docs/contributing/iteration/engine.md`
   - Changes: retarget to `load/index.md` for general "Load the Warehouse" pointers; `load/sources.md#cursor-sessionsmodels-enrichment` for the model-enrichment link; `load/schedule.md` for the `#scheduling` link; `../basic.md#ingest` for the two backfill `#ingest` anchors; `load/backfill/…` for backfill paths.
   - Verify: B5, B6; re-run build and confirm group A warnings gone

5. **Repair group B links (`contributing/iteration/` nest)**
   - Files: `docs/advanced/duckdb.md`, `docs/architecture/{backfill,lifecycle,packaging,warehouse}.md`, `docs/contributing/{index,preparation}.md`, `docs/contributing/iteration/{index,engine,skills,dashboard,backfill-adapters}.md`
   - Changes: `contributing/iteration.md` → `contributing/iteration/index.md`; `contributing/backfill-adapters.md` → `contributing/iteration/backfill-adapters.md`; inside `iteration/`, `preparation.md` → `../preparation.md` and cross-tree `../x/` → `../../x/`. Also update the prose path in `backfill-adapters.md:43` (`user-guide/ingest/backfill/` → `user-guide/load/backfill/`).
   - Verify: re-run build; group B warnings gone

5b. **Fix the stale docs path in shipped skill payload** *(preflight amendment A1)*
   - Files: `skills/sr-initialize/SKILL.md`
   - Changes: line 47 references `docs/contributing/iteration.md`, which no longer exists → `docs/contributing/iteration/index.md`. Line 99's torch.md reference is still valid — leave it.
   - Verify: path resolves on disk. The docs build cannot catch this (outside `docs_dir`), so it is a read-and-confirm check.

6. **Fix stale memory-bank pointers**
   - Files: `memory-bank/systemPatterns.md`, `memory-bank/techContext.md`
   - Changes: both reference `docs/contributing/iteration.md`, which no longer exists → `docs/contributing/iteration/index.md`. Surgical link fix only.
   - Verify: paths resolve on disk

7. **Final strict build**
   - Files: none (read-only)
   - Changes: `make docs-build` → exit 0, zero warnings; re-read the three `load/` pages against B1–B3
   - Verify: B7

## Technology Validation

No new technology - validation not required.

## Dependencies

- Existing ProperDocs toolchain (`make docs-build`, root `pyproject.toml` docs group)
- Prior rework's backfill page bodies stay as shipped (link targets only)
- `docs/contributing/.pages` and `docs/contributing/iteration/.pages` already updated by the operator's earlier move

## Challenges & Mitigations

- **Slug regression on the models-enrichment heading**: the exact heading text must move verbatim; B5 is a build-enforced check, so a slip fails the build rather than shipping silently.
- **Group B balloons the diff**: it is 19 mechanical link fixes across 11 files with no prose changes. If any file needs actual rewriting to fix a link, stop and re-scope rather than absorbing it.
- **Router loses content someone linked to**: `load/index.md` currently has no anchors that anything links to (baseline warnings confirm the only inbound anchor request is `#ingest`, which never existed there). Safe to replace wholesale.
- **`sources.md` becomes a second junk drawer**: admit only content that is per-harness. Anything that would read identically for a hypothetical third harness belongs in `basic.md`.

## Pre-Mortem

- **We fix links one at a time and miss some**: the build enumerates every failure by file and target, so work the warning list to zero rather than grepping by hand; re-run after each group.
- **Group B turns out to be mid-flight operator work we just clobbered**: the nest is already committed (`7cc9ae8`) and `.pages` files are updated, so it is finished work with stale inbound links — not in progress. Verified before planning.
- **Zero-warning is the wrong bar because some warnings predate everything**: checked — all 38 trace to the two renames; there is no pre-existing warning floor to grandfather.
- **The split leaves `basic.md` as the new dumping ground**: B3 asserts what belongs there positively, not just "whatever is left over."

## Preflight Amendments (2026-07-26)

- **A1 — new step 5b.** `skills/sr-initialize/SKILL.md:47` points at `docs/contributing/iteration.md`. It is shipped skill payload outside `docs_dir`, so the strict build will never flag it; without this step the rework ships a stale path while claiming a clean tree. Confirmed by scanning `skills/`, `README.md`, and `.github/` — this is the only such reference (line 99's torch.md target is unmoved).
- **A2 — name the new page "Harness Sources", not "Sources".** `load/backfill/index.md` already defines "source" as *a named legacy store*, with its own Sources table. A sibling page titled "Sources" puts two meanings of the word one nav level apart. H1 and nav label become **Harness Sources**; filename stays `sources.md`.
- **A3 — slug claim verified, not assumed.** `properdocs.yaml` configures `pymdownx.slugs.slugify(case: lower)` (GitHub-compatible). Slugs derive from heading *text* only, so `Cursor \`sessions.models\` Enrichment` yields `cursor-sessionsmodels-enrichment` at any heading level. Step 2's demotion of that heading is safe; B5 still gates it.
- **A4 — `.pages` becomes authoritative the moment it exists.** `validation.omitted_files: warn` under `strict: true` means a file present in `load/` but absent from `load/.pages` fails the build. Today `load/` has no `.pages`, so files are auto-included. Step 3 must list all five entries including the brand-new `sources.md`, or Step 7 fails.
- **A5 — no test changes required.** Scanned `skills/sr-search/tests/`: the only docs-path assertions are `test_query_cookbook.py` (`docs/advanced/cookbook`) and `test_torch_source.py` (torch.md). Neither path is touched.

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Pre-Mortem complete
- [ ] Preflight
- [ ] Build
- [ ] QA
