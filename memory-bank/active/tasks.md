# Task: contributing-development-guide

* Task ID: contributing-development-guide
* Complexity: Level 2
* Type: simple enhancement (documentation)

Rework `docs/contributing/development.md` into a day-to-day contributor guide assuming Local workflow setup is done. Cover prerequisites, engine, Torch (including trying new Torches), docs site, dashboard, and skills; refresh the `make` reference to match the current Makefile. Keep enter/verify/exit owned by `local-workflow.md`.

## Test Plan (TDD)

### Behaviors to Verify

- [Entry assumption]: Reader opens Development → first screen points to Local workflow for enter/verify/exit and does not re-own the rip-it-out ritual
- [Prerequisites]: Page lists what you need before day-to-day work (uv, Node 22 for full gate, wired local checkout) → actionable, not marketplace bootstrap
- [Engine]: Reader can find where engine code lives, how to sync/lock/test/lint, and how to invoke via `stockroom` → concrete commands from repo root
- [Torch restore vs change]: After `make sync`/`make ci`, restore via `stockroom shim ensure-env` (freeze) is distinguished from deliberately changing stack via `make torch TORCH_INDEX=…` → matches local-workflow footgun and torch.md
- [Try new Torch]: Reader can install alternate index, smoke, freeze → steps present without duplicating full operator torch.md
- [Docs site]: Reader can preview (`make docs`) and strict-build (`make docs-build`); two-uv-projects / publishing notes remain accurate
- [Dashboard]: Reader knows static ESM path, Node 22 `make test-js`, bounce via `stockroom dashboard` / `make local-dashboard`, link to user-guide for product semantics
- [Skills]: Reader knows `skills/*/SKILL.md` edit surface, Cursor mirror vs Claude `--plugin-dir`, and wrapper hygiene (`stockroom <cmd>` only / `test_skill_hygiene`)
- [Make table]: Targets listed match current `make help` semantics; localdev atoms are briefly pointed at Local workflow rather than re-documented
- [No regression]: `make docs-build` succeeds; contributing nav (`.pages`) still orders local-workflow before development

### Edge Cases

- [Duplicate localdev]: Development must not become a second SSOT for enter/clean/status → mitigate by short pointer + optional one-line “atoms live in Local workflow”
- [Torch advice conflict]: Must not tell contributors to `make torch` after every sync (rewrites freeze) → ensure-env vs make torch called out
- [Empty / wrong audience]: Must not present `make`/`uv` as end-user bootstrap → `sr-initialize` stays the operator onboarding path when mentioned
- [Stale make list]: Omitting `format-check` or mis-describing local-* → build step diffs against live `make help`

### Test Infrastructure

- Framework: properdocs strict build (`make docs-build`); no pytest suite for contributing markdown prose
- Test location: N/A for content assertions — verification checklist below + `make docs-build`
- Conventions: Prior contributing/user-guide docs work verified the same way (strict build + content review against acceptance criteria)
- New test files: none
- Note: Workspace TDD rule targets code behavior. This task is documentation-only; “failing tests first” maps to writing the verification checklist before editing `development.md`, then proving it with `docs-build` + checklist pass

## Implementation Plan

1. **Rewrite `docs/contributing/development.md` structure** (content-first draft in place)
   - Files: `docs/contributing/development.md`
   - Changes: Replace current Makefile-dump-first layout with ordered sections:
     1. Short intro + Local workflow pointer
     2. Prerequisites
     3. Make targets (table grouped: env/quality, torch, docs, localdev pointer)
     4. Engine (`skills/sr-search/`, sync/lock/test/lint/format, `stockroom` invocation, keep bootstrap footnote lean)
     5. Torch (contract summary, ensure-env vs `make torch`, try new index + smoke + freeze, link `../user-guide/troubleshooting/torch.md`)
     6. Docs site (root stub project, `make docs` / `docs-build`, publishing / Pages note)
     7. Dashboard (static under `skills/sr-search/src/stockroom/dashboard/static/`, Python package tests, `make test-js`, bounce, link user-guide dashboard)
     8. Skills (`skills/*/SKILL.md`, Cursor `local-skills` mirror, Claude `--plugin-dir`, hygiene + `tests/test_skill_hygiene.py`)
   - Preserve accurate facts already present (two uv projects, torch-safe flags, publishing Pages step) while cutting localdev narrative duplication

2. **Align Make table with live Makefile**
   - Files: `docs/contributing/development.md`
   - Changes: Sync target names/descriptions to `make help` (include `format-check`; do not invent targets). Localdev rows: one-line role + “see Local workflow” rather than full atom docs

3. **Light cross-link pass**
   - Files: `docs/contributing/index.md` (only if funnel text still implies Development owns localdev), `docs/contributing/local-workflow.md` (Torch footgun already links Development — keep consistent wording)
   - Changes: Minimal edits only if wording would contradict the new Development shape; prefer leave local-workflow alone if already correct

4. **Verify**
   - Run `make docs-build`
   - Walk Test Plan behaviors checklist against rendered/source markdown
   - Spot-check `make help` vs Make table

## Technology Validation

No new technology - validation not required

## Dependencies

- Accurate current Makefile / local-workflow / torch.md (already in tree)
- Prior contributing-localdev-guide archive for ownership split (workflow vs development)

## Challenges & Mitigations

- [Scope creep into localdev]: Mitigate by hard section budget — Development never documents rip-it-out, clean, or FORCE semantics beyond a link
- [Torch section becomes a second torch.md]: Mitigate — contributor-facing “day-to-day + try new” only; operator remedies stay in user-guide torch.md
- [Skills section underspecified]: Mitigate — document edit location + harness reload path + hygiene gate; do not invent a skills “hot reload” story Make does not provide
- [Docs-only vs always-tdd]: Mitigate — checklist-first + `docs-build` as the automated gate; no fake pytest for prose

## Pre-Mortem

- [Plan failed because Development still opened with a giant undifferentiated make dump and buried the five surfaces]: Structure step 1 as section-first; Make table is supporting reference, not the article
- [Plan failed because ensure-env vs make torch was blurred and contributors rewrote freezes after every sync]: Already covered by Challenge + explicit Torch behavior in Test Plan
- [Plan failed because skills/dashboard advice assumed marketplace hooks still install]: Point at Local workflow for wiring; dashboard bounce via CLI; skills via mirror / `--plugin-dir`
- [Wrong level — needed creative for IA]: Unlikely; section order is given by operator; FAIL-to-relevel only if build reveals conflicting SSOT requirements across many docs

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Pre-Mortem complete
- [ ] Preflight
- [ ] Build
- [ ] QA
