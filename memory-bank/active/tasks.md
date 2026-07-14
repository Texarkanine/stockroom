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

1. **Lock acceptance gate (before content edits)**
   - Files: `memory-bank/active/tasks.md` (Test Plan behaviors — already written)
   - Changes: Treat each Behavior / Edge Case as a must-pass assertion. Do not edit `development.md` until this gate is explicit. (Docs-only TDD: checklist = tests.)

2. **Rewrite `docs/contributing/development.md` to satisfy the checklist**
   - Files: `docs/contributing/development.md`
   - Changes: Replace Makefile-dump-first layout with ordered sections that map 1:1 to behaviors:
     1. Short intro + Local workflow pointer + **surface jump list** (Engine / Torch / Docs / Dashboard / Skills)
     2. Prerequisites
     3. Make targets (table grouped: env/quality, torch, docs, localdev pointer — matched to live `make help`)
     4. Engine (`skills/sr-search/`, sync/lock/test/lint/format/`format-check`, `stockroom` invocation, lean bootstrap footnote)
     5. Torch (contract summary, ensure-env vs `make torch`, try new index + smoke + freeze, link torch.md)
     6. Docs site (root stub project, `make docs` / `docs-build`, publishing / Pages note)
     7. Dashboard (static under `…/dashboard/static/`, Python tests, `make test-js`, bounce, user-guide link)
     8. Skills (`skills/*/SKILL.md`, Cursor mirror / Claude `--plugin-dir`, hygiene + `test_skill_hygiene`)
   - Preserve accurate facts (two uv projects, torch-safe flags, Pages step); cut localdev narrative duplication

3. **Light cross-link pass**
   - Files: `docs/contributing/index.md` and/or `local-workflow.md` only if wording contradicts the new Development shape
   - Changes: Minimal; prefer leave alone when already correct

4. **Execute verification (must fail any unmet checklist item → fix → re-run)**
   - Run `make docs-build`
   - Walk every Test Plan behavior and edge case against the rewritten page
   - Spot-check Make table against `make help`

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

## Build Progress

- [x] 1. Lock acceptance gate
- [x] 2. Rewrite `development.md` (jump list + five surfaces + make table)
- [x] 3. Light cross-link pass (`index.md`, `CONTRIBUTING.md`; local-workflow unchanged)
- [x] 4. Verification: `make docs-build` PASS; content checklist PASS (entry check: Local workflow linked; rip-it-out named only as pointer, not a second ritual)
- [x] Post-reflect: per-section Make targets; renamed to `preparation.md` / `iteration.md`; `test-dashboard-js` + `test-dashboard-py`; Skills restyle

## QA Results

- Completeness: all brief requirements covered; make table includes full `make help` set
- KISS/DRY: trivial polish — `HARNESS` cell wording, `ensure-env` language consistency, added `help` row
- YAGNI: no speculative surfaces
- Regression: local-workflow remains SSOT for enter/exit; torch.md remains operator remedies
- Integrity: no scaffolding
- Documentation: primary deliverable; funnel pages updated

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Pre-Mortem complete
- [x] Preflight
- [x] Build
- [x] QA
