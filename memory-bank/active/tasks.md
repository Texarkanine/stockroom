# Task: release-quality-docs

* Task ID: release-quality-docs
* Complexity: Level 2
* Type: documentation content draft (ingest page)

Draft `docs/user-guide/ingest.md` to finished user-guide quality (ingest / embed / scheduling), matching Quickstart / Installed layout / Torch troubleshooting style. Treat operator WIP (torch under `troubleshooting/`, stub search/dashboard) as the working base — fix only link breakage that blocks `make docs-build`.

## Test Plan (TDD)

Docs-only — always-tdd code cycle does **not** apply (same as prior reworks on this task id). **Verification Plan** is the gate:

1. Acceptance sweep against behaviors B1–B5 (and edge cases E1–E3) **before** claiming build complete.
2. `make docs-build` (`properdocs build --strict`).
3. Spot-check relative links from ingest page resolve in the source tree.

Ordered build discipline: draft + link reconcile first, then run the Verification Plan (do not treat a green build alone as acceptance).

### Behaviors to Verify

- **B1 Mental model**: Reader opening `docs/user-guide/ingest.md` → understands ingest vs embed vs schedule as three distinct jobs (ETL → vectors → nightly freshness), without opening contributing. ✅
- **B2 First-run vs ongoing**: Page explains `sr-initialize` already ran first `ingest --full` + `embed`, and ongoing freshness is incremental nightly (or manual CLI) — does not re-own the Quickstart marketplace ritual. ✅
- **B3 Operator commands**: Page shows the common re-run commands (`stockroom ingest`, `stockroom embed`, `stockroom schedule status|install|remove`) with accurate defaults (`--full` / `--verbose` as optional; schedule default 03:30) grounded in product behavior — not a SKILL.md flag encyclopedia. ✅
- **B4 DRY links**: Points at Quickstart (get running), Installed layout (warehouse / schedule on disk), Torch troubleshooting (embed needs torch), Advanced CLI (escape hatch / env overrides), Troubleshooting (staleness) — does not fork those contracts. ✅
- **B5 Style + build**: Tone/density matches finished examples; no todo placeholders; `make docs-build` PASS. ✅

### Edge cases

- **E1 WIP torch path**: Retargeted inbound links to `troubleshooting/torch.md`; fixed troubleshooting/ relative parents. ✅
- **E2 Empty sibling stubs**: `search.md` / `dashboard.md` got minimal H1 + TODO (not fleshed). ✅
- **E3 No warehouse prune**: Documented in Ingest section. ✅

### Test Infrastructure

- Framework: properdocs strict build / `make docs-build`
- New test files: none
- Conventions: docs-only verification (same as prior reworks on this task id)

## Implementation Plan

1. **Draft ingest page body** ✅
   - Files: `docs/user-guide/ingest.md`
2. **Reconcile WIP path moves for strict build** ✅
   - Files: installed-layout, quickstart, troubleshooting/index, development.md, CONTRIBUTING, systemPatterns, techContext, sr-initialize; search/dashboard H1 stubs
3. **Verify** ✅
   - `make docs-build` PASS; `make reuse` PASS; acceptance B1–B5

## Technology Validation

No new technology - validation not required

## Dependencies

- Finished style examples: `docs/user-guide/quickstart.md`, `installed-layout.md`, `troubleshooting/torch.md`
- Product behavior SSOT for agents: `skills/sr-initialize/SKILL.md` (docs paraphrase, do not fork flag tables)
- Escape hatch: `docs/advanced/cli.md`
- Operator WIP base tree (torch under troubleshooting/)

## Challenges & Mitigations

- **Challenge — Overlap with Advanced CLI / sr-initialize**: Mitigation — user-guide owns *why / when / what to expect*; Advanced owns flag escape hatch; Quickstart owns first ritual; one short command block on ingest page is enough.
- **Challenge — WIP breaks strict build before we touch ingest**: Mitigation — Step 2 surgical link retarget only; do not expand into another IA rework.
- **Challenge — Inventing CLI details**: Mitigation — verify every flag/default against CLI/`sr-initialize` before writing; prefer `--help` / Advanced CLI deferral for rare options.

## Pre-Mortem

- **Page becomes a second initialize guide**: Cut bootstrap steps; lead with “after Quickstart” and link out.
- **Flag table drift from SKILL.md**: Already covered by Challenge — keep commands illustrative, defer encyclopedias.
- **Verification green while prose wrong**: Acceptance sweep B1–B4 before declaring build PASS sufficient.

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Pre-Mortem complete
- [x] Preflight
- [x] Build
- [ ] QA
