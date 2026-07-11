# Task: reuse-ppls-narrow-carveout

* Task ID: reuse-ppls-narrow-carveout
* Complexity: Level 2
* Type: simple enhancement

Invert REUSE PPL-S from blanket `skills/**` to a narrow carve-out (`SKILL.md` + `references/**`), drop AGPL claw-back re-asserts, update licensing tests and system-patterns prose, and verify with SPDX before/after.

## Test Plan (TDD)

### Behaviors to Verify

- [B1 PPL-S SKILL.md]: `skills/sr-search/SKILL.md` → resolves to `LicenseRef-PPL-S`
- [B2 PPL-S references]: `skills/sr-search/references/system-model.md` → resolves to `LicenseRef-PPL-S`
- [B3 AGPL code without claw-back]: `skills/sr-search/src/stockroom/__init__.py` → `AGPL-3.0-or-later` only (not PPL-S)
- [B4 AGPL shell]: `skills/sr-search/src/stockroom/shim_template.sh` → AGPL only
- [B5 AGPL dashboard assets]: authored static HTML/mjs and `tests-js/**` → AGPL only (inherit base; no re-assert block required)
- [B6 Chart.js MIT]: vendored Chart.js → MIT only
- [B7 fixture README stays AGPL]: `skills/sr-search/tests/fixtures/transcripts/README.md` → AGPL (not painted PPL-S by `*.md` blanket)
- [B8 reuse lint]: whole tree `reuse lint` → exit 0
- [B9 SPDX delta]: before vs after SPDX → only expected path license flips

### Test Infrastructure

- Framework: pytest (configured in `skills/sr-search/pyproject.toml`)
- Test location: `skills/sr-search/tests/test_licensing.py`
- Conventions: module docstring describes layered model; helpers `_run_reuse` / `_spdx_license_map`; assert via `reuse spdx` map
- New test files: none — extend existing `test_licensing.py`

## Implementation Plan

1. [x] **SPDX baseline**
   - Files: `/tmp/stockroom-reuse-spdx/before.spdx` (already captured)
   - Changes: none in-repo

2. [ ] **Failing/updated licensing assertions (TDD)**
   - Files: `skills/sr-search/tests/test_licensing.py`
   - Changes: update module docstring to inverted model; add assertions for `references/system-model.md` PPL-S and fixture README AGPL; keep code/shell/dashboard/Chart.js assertions; remove any implication that claw-back re-assert is required for AGPL

3. [ ] **REUSE.toml invert**
   - Files: `REUSE.toml`
   - Changes: replace `skills/**` PPL-S with `skills/**/SKILL.md` + `skills/**/references/**`; delete rules 3 and 4; renumber comments; keep Chart.js MIT and `.cursor` NOASSERTION

4. [ ] **systemPatterns blurb**
   - Files: `memory-bank/systemPatterns.md`
   - Changes: surgical update to "Layered licensing" to describe narrow PPL-S carve-out (no claw-back)

5. [ ] **Verify**
   - Run licensing tests + `make reuse` / `reuse lint`
   - Save `/tmp/stockroom-reuse-spdx/after.spdx`; diff licenses vs before; report flips

## Technology Validation

No new technology - validation not required

## Dependencies

- Existing `reuse` CLI and `test_licensing.py` SPDX helpers
- SPDX baseline already at `/tmp/stockroom-reuse-spdx/before.spdx`

## Challenges & Mitigations

- **Challenge: SPDX before/after noise from unrelated path churn.** Mitigation: compare only `FileName` → `LicenseInfoInFile` pairs; ignore Package-level metadata; report only paths whose license set changed.
- **Challenge: REUSE glob semantics for `skills/**/references/**` miss nested files or over-match.** Mitigation: after edit, assert `system-model.md` is PPL-S via `reuse spdx` / licensing test before declaring done.
- **Challenge: dropping rule 4 leaves dashboard assets looking "unasserted" in comments.** Mitigation: comments document that they inherit base AGPL; tests still pin AGPL on those paths.

## Pre-Mortem

- **Plan failed because we used `skills/**/*.md` and flipped the fixture README to PPL-S:** already covered — brief requires SKILL.md + references only; B7 asserts README stays AGPL.
- **Plan failed because SPDX diff showed unexpected flips we didn't notice:** covered by B9 + explicit before/after save and license-set comparison script in verify step.
- **Plan failed because we left stale claw-back comments/tests claiming re-assert is load-bearing:** step 2 docstring + step 3 comment renumber address this.

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Pre-Mortem complete
- [ ] Preflight
- [ ] Build
- [ ] QA
