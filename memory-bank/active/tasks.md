# Task: p5-m3-release-e2e-spine

* Task ID: p5-m3-release-e2e-spine
* Complexity: Level 3
* Type: feature (distribution proof)

Exercise release-please version sync into both plugin manifests, then prove the full spine on a clean machine: marketplace add → install → `sr-initialize` → `sr-search` / `sr-semantic` / `sr-query` / `sr-dashboard` against real Cursor and Claude Code history.

## Pinned Info

### m3 proof spine

Release half is already landed; remaining work is verify + operator-driven marketplace E2E under an isolated warehouse home.

```mermaid
flowchart TD
    R["Release-please already cut<br/>v0.1.0 / v0.1.1 lockstep"] --> V["Verify evidence<br/>PRs #10/#11 + packaging tests"]
    V --> Prep["Agent: prepare E2E runbook<br/>STOCKROOM_HOME isolation"]
    Prep --> Op["Operator: marketplace add + install<br/>Cursor AND Claude"]
    Op --> Init["Operator: sr-initialize<br/>both harness forms"]
    Init --> Surfaces["Prove four surfaces<br/>search / semantic / query / dashboard"]
    Surfaces --> Done["Roadmap Phase 5 checkboxes<br/>+ reflection evidence"]
```

## Component Analysis

### Affected Components
- **release-please / plugin manifests**: Already sync `$.version` into `.cursor-plugin/plugin.json` and `.claude-plugin/plugin.json` via `extra-files`. m3 verifies live cuts (v0.1.0, v0.1.1) — no config change expected unless lockstep is broken.
- **Packaging tests** (`skills/sr-search/tests/test_packaging.py`): Already assert config presence, version lockstep, and `extra-files` targets. Remain the automated regression bar; no new product tests for UI marketplace install.
- **Marketplace catalog** (`txrk9-agent-plugins`): PR #2 merged — stockroom in both Cursor and Claude `marketplace.json`. Prerequisite for E2E; no further catalog edits in m3.
- **Install/usage docs** (`README.md`): Already document marketplace path + local/dev loaders (m1). Touch only if E2E reveals a factual error.
- **Onboarding / surfaces** (`sr-initialize`, `sr-search`, `sr-semantic`, `sr-query`, `sr-dashboard`): Exercised as-is under isolated `STOCKROOM_HOME`; no engine redesign.
- **Roadmap** (`planning/roadmap.md`): Phase 5 checkboxes still open for the release+E2E milestone — update when proof lands.
- **Memory bank**: Creative decision + E2E evidence for reflect/archive; persistent files only if E2E teaches a lasting pattern.

### Cross-Module Dependencies
- Marketplace catalog (merged) → harness UI install → plugin root → `sr-initialize` resolves `APP_DIR` → on-path `stockroom` → warehouse under `STOCKROOM_HOME` / XDG → four surfaces read that warehouse.
- Release-please → tagged source at GitHub → marketplace `source.repo` points at that repo (no version pin in catalog).

### Boundary Changes
- None to public engine APIs or marketplace schema.
- Operational boundary: E2E uses a throwaway `STOCKROOM_HOME`; does not mutate the operator's default warehouse unless they choose to.

### Invariants & Constraints
- Dual-manifest, no-build; versioning in stockroom only; on-path engine invocation; both harnesses always; slobac + official docs as correctness bar; marketplace is a separate repo.

## Open Questions

- [x] **Clean-machine E2E methodology** → Resolved: same-host isolation via fresh `STOCKROOM_HOME` + marketplace reinstall (not local/dev loaders); operator-driven UI install; agent prepares runbook and verifies CLI outcomes. Release half = verify existing cuts, do not re-cut. (see `memory-bank/active/creative/creative-clean-machine-e2e.md`)

## Test Plan (TDD)

### Behaviors to Verify

- **Release lockstep (automated)**: packaging suite → both plugin manifests and `.release-please-manifest.json` share one version; `extra-files` targets both `plugin.json` paths.
- **Release evidence (ephemeral assert)**: GitHub releases `v0.1.0` / `v0.1.1` exist; release PR #11 touched both plugin manifests + manifest + CHANGELOG.
- **Marketplace prerequisite (ephemeral assert)**: `txrk9-agent-plugins` main catalogs include `stockroom` → `Texarkanine/stockroom` with no version field (both harnesses).
- **Clean warehouse (operator + agent)**: with `STOCKROOM_HOME` pointing at an empty dir → after `sr-initialize`, warehouse populates under that home (not the default share path).
- **Four surfaces (operator + agent)**: under that home, `stockroom search` / `semantic` / `query` / `dashboard` (or skill forms) succeed against real Cursor and Claude history.
- **Both harnesses (operator)**: marketplace install + skill invocation forms work in Cursor (`/sr-*`) and Claude (`/stockroom:sr-*`).

### Edge Cases

- Local/dev plugin still loaded → false "install" — runbook must uninstall/disable local loaders first.
- Default warehouse already populated → not a clean proof — require fresh `STOCKROOM_HOME`.
- Marketplace not yet visible in UI after merge → wait/refetch; do not fall back to `--plugin-dir` as the primary claim.
- Release lockstep broken → stop and fix packaging/release config before E2E.

### Test Infrastructure

- Framework: pytest under `skills/sr-search/tests/` (existing packaging tests)
- Conventions: packaging/contract tests for install artifacts; no CI pins on README prose (m1 lesson)
- New test files: **none** — marketplace UI and clean-machine spine are operator proofs, not unit tests
- Ephemeral asserts: shell/python one-shots during build (same pattern as m2), not committed

### Integration Tests

- No new automated integration suite. Cross-component proof is the operator E2E runbook + captured evidence.

## Implementation Plan

Each step is verify-first (assert / test before any mutation). There is no greenfield product code unless step 6 triggers a defect fix.

1. **Verify release-please exercise (already landed)** — TDD: assert before mutate
    - Red/verify: run `skills/sr-search/tests/test_packaging.py` (must pass). Ephemeral asserts: tags `v0.1.0`/`v0.1.1` exist; PR #11 files include both plugin manifests + `.release-please-manifest.json`.
    - Green/mutate: only if asserts fail — fix release-please config / manifests under packaging-test guidance, then re-run tests. **Do not open a new release PR unless lockstep is broken.**
    - Files: `.release-please-manifest.json`, `.cursor-plugin/plugin.json`, `.claude-plugin/plugin.json`, `skills/sr-search/tests/test_packaging.py`
    - Creative ref: `creative-clean-machine-e2e.md` (verify, don't re-cut)

2. **Confirm marketplace prerequisite** — TDD: assert before mutate
    - Red/verify: ephemeral JSON asserts on `txrk9-agent-plugins` `main` — both catalogs include `stockroom` → `Texarkanine/stockroom`, no version field.
    - Green/mutate: none expected (m2 delivered). If asserts fail → stop; do not invent catalog edits inside m3 without re-scoping.
    - Files: `txrk9-agent-plugins` `.cursor-plugin/marketplace.json`, `.claude-plugin/marketplace.json` (read-only)

3. **Author operator E2E runbook** — docs-only (no production code)
    - Verify: runbook covers every behavior in the Test Plan (isolation, both harnesses, four surfaces, evidence capture).
    - Files: `memory-bank/active/e2e-clean-machine-runbook.md` (ephemeral; distilled into reflection/archive)
    - Changes: Ordered checklist — disable local/dev loads; add marketplace URL; install stockroom in Cursor and Claude; `export STOCKROOM_HOME=…` (empty dir); run initialize both harness forms; exercise four surfaces; capture outputs/URLs; note pass/fail per step.

4. **Execute E2E with operator** — assert outcomes as evidence
    - Verify: each runbook step records pass/fail + captured output before marking complete.
    - Files: none in-repo product code; evidence lands in the runbook
    - Changes: Operator performs UI steps; agent assists with CLI verification under `STOCKROOM_HOME` (`stockroom doctor`, query counts, surface smokes).

5. **Close Phase 5 bookkeeping** — only after step 4 evidence is green
    - Verify: runbook shows release evidence + E2E spine pass for both harnesses (or documents an explicit harness blocker).
    - Files: `planning/roadmap.md` (Phase 5 checkboxes), memory-bank progress/tasks
    - Changes: Check off release flow + end-to-end install test / done-when criteria. Fix README only if E2E found a factual doc bug (doc fix is content correction, not a new feature).

6. **Defect repair (conditional)** — full TDD cycle if E2E finds a product bug
    - Stub/write failing test in the owning component → implement → re-run tests → re-run affected E2E step.
    - Scoped repair inside this build, not a new milestone.

## Technology Validation

No new technology - validation not required. Uses existing release-please, marketplace, `STOCKROOM_HOME`, and on-path `stockroom`.

## Challenges & Mitigations

- **Marketplace UI not agent-automatable**: Mitigation — operator-driven runbook; agent owns prep + CLI verification only.
- **False clean from local plugin / default warehouse**: Mitigation — runbook requires disabling local loaders and a fresh `STOCKROOM_HOME`.
- **Release already done — risk of scope creep into another bump**: Mitigation — creative decision: verify existing cuts; re-cut only if lockstep broken.
- **E2E finds product bugs**: Mitigation — fix under normal TDD in-scope; do not invent a Phase 6.
- **Harness history missing on this host**: Mitigation — unlikely for the operator's box; if a harness has zero data, document which harness was proven and whether the other is blocked.

## Preflight Amendments

- **TDD encoding**: Rewrote implementation steps 1–6 so each unit is assert/verify-before-mutate (packaging tests + ephemeral asserts before any release/catalog change; runbook evidence before roadmap checkboxes; conditional defect repair is an explicit red→green cycle).

## Status

- [x] Component analysis complete
- [x] Open questions resolved
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Preflight
- [ ] Build
- [ ] QA
