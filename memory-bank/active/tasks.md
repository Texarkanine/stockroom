# Task: release-quality-docs

* Task ID: release-quality-docs
* Complexity: Level 2
* Type: documentation content draft (ingest page)

Draft `docs/user-guide/ingest.md` to finished user-guide quality (ingest / embed / scheduling), matching Quickstart / Installed layout / Torch troubleshooting style. Treat operator WIP (torch under `troubleshooting/`, stub search/dashboard) as the working base — fix only link breakage that blocks `make docs-build`.

## Test Plan (TDD)

Docs-only — always-tdd code cycle does **not** apply. Verification Plan:

1. Acceptance sweep against behaviors B1–B5.
2. `make docs-build` (`properdocs build --strict`).
3. Spot-check relative links from ingest page resolve in the built site / source tree.

### Behaviors to Verify

- **B1 Mental model**: Reader opening `docs/user-guide/ingest.md` → understands ingest vs embed vs schedule as three distinct jobs (ETL → vectors → nightly freshness), without opening contributing.
- **B2 First-run vs ongoing**: Page explains `sr-initialize` already ran first `ingest --full` + `embed`, and ongoing freshness is incremental nightly (or manual CLI) — does not re-own the Quickstart marketplace ritual.
- **B3 Operator commands**: Page shows the common re-run commands (`stockroom ingest`, `stockroom embed`, `stockroom schedule status|install|remove`) with accurate defaults (`--full` / `--verbose` as optional; schedule default 03:30) grounded in product behavior — not a SKILL.md flag encyclopedia.
- **B4 DRY links**: Points at Quickstart (get running), Installed layout (warehouse / schedule on disk), Torch troubleshooting (embed needs torch), Advanced CLI (escape hatch / env overrides), Troubleshooting (staleness) — does not fork those contracts.
- **B5 Style + build**: Tone/density matches finished examples; no todo placeholders; `make docs-build` PASS.

### Edge cases

- **E1 WIP torch path**: Working tree has torch at `troubleshooting/torch.md` (not `user-guide/torch.md`). Ingest links and any blocked inbound links from installed-layout / quickstart / contributing must match files that exist, or strict build fails.
- **E2 Empty sibling stubs**: `search.md` / `dashboard.md` remain empty stubs — do not flesh them in this rework; ensure they do not break strict build (minimal H1 if required).
- **E3 No warehouse prune**: Document that ingest does not delete orphaned rows when source transcripts vanish (faithful warehouse outlives sources) — one accurate sentence, not a schema essay.

### Test Infrastructure

- Framework: properdocs strict build / `make docs-build`
- New test files: none
- Conventions: docs-only verification (same as prior reworks on this task id)

## Implementation Plan

1. **Draft ingest page body**
   - Files: `docs/user-guide/ingest.md`
   - Changes: Replace stub with finished draft. Suggested structure (adjust lightly if prose flows better):
     - Title + short lead (what this page is for — post-Quickstart mental model)
     - **Ingest** — harness history → DuckDB (`sessions` / `messages` / `tool_calls`); incremental vs `--full`; Cursor + Claude; points at warehouse path via Installed layout
     - **Embed** — message text → vectors; needs torch; incremental vs `--full`; first-run timing expectations; link Torch troubleshooting
     - **Scheduling** — nightly `ingest && embed` via cron/launchd; consent via `sr-initialize`; `schedule status|install|remove`; log path under stockroom home; warn about cron daemon not running
     - Short “re-run anytime” command block + link to Advanced CLI for env overrides / `--help`
   - Ground facts in `sr-initialize` SKILL + engine modules; do not invent flags.

2. **Reconcile WIP path moves for strict build**
   - Files (only if still broken): `docs/user-guide/installed-layout.md`, `docs/user-guide/quickstart.md`, `docs/contributing/development.md`, optionally `docs/user-guide/.pages` / empty `search.md`/`dashboard.md` H1s
   - Changes: Retarget `torch.md` → `troubleshooting/torch.md` (or relative equivalent); `troubleshooting.md` → `troubleshooting/` or `troubleshooting/index.md`; do **not** reverse the torch→troubleshooting move.
   - Out of scope: fleshing search/dashboard, rewriting troubleshooting index content, README/CONTRIBUTING torch path outside docs unless needed for this task’s acceptance.

3. **Verify**
   - Files: none (commands only)
   - Changes: Acceptance sweep B1–B5; `make docs-build`; fix any new link breakage introduced by the draft.

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
- [ ] Preflight
- [ ] Build
- [ ] QA
