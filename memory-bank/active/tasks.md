# Task: release-quality-docs

* Task ID: release-quality-docs
* Complexity: Level 2
* Type: documentation IA rework (torch placement)

Move the torch operator contract from `docs/contributing/torch.md` to `docs/user-guide/torch.md`. Keep contributor-only mechanics under contributing (`development.md`). Retarget nav and inbound links. Per `projectbrief.md` Rework 2.

## Test Plan (TDD)

Docs-only — always-tdd code cycle does **not** apply. Verification Plan:

1. Acceptance sweep against behaviors B1–B5.
2. `make docs-build` (`properdocs build --strict`).
3. `make reuse` if new paths need aggregates (expected: no change).

### Behaviors to Verify

- **B1 User-guide SSOT**: `docs/user-guide/torch.md` exists in nav and owns why-out-of-lock, install→smoke→freeze, heal-from-freeze, user failure remedies.
- **B2 No contributing fork of operator contract**: contributing does not duplicate the full heal essay; at most points at user-guide + keeps `make torch` / manual freeze / shared-deps.
- **B3 Troubleshooting**: Torch/embeddings rows link to user-guide torch (not contributing).
- **B4 Installed layout**: torch artifact rows link to user-guide torch for deeper contract.
- **B5 Links**: CONTRIBUTING, development.md, sr-initialize, techContext/systemPatterns, and any other inbound refs resolve; `make docs-build` PASS.

### Edge cases

- **E1** Artifact tables: user-guide torch may summarize roles and link Installed layout rather than duplicate the path table.
- **E2** Operator WIP on `installed-layout.md` (path table, shortened page) is base tree — preserve; add torch links surgically.

### Test Infrastructure

- Framework: properdocs strict build / `make docs-build`
- New test files: none

## Implementation Plan

1. **Create user-guide torch page**
   - Files: `docs/user-guide/torch.md`; `docs/user-guide/.pages` (add Torch entry near Installed layout / before troubleshooting)
   - Changes: Operator contract from current contributing torch (why, contract steps, heal, writers relevant to users (`sr-initialize` + heal), failure table). Link Installed layout for path rows. Do not include `make torch` / PYTHONPATH bootstrap as primary path.

2. **Shrink contributing torch surface**
   - Files: delete `docs/contributing/torch.md` *or* replace with short “Torch for contributors” that only covers `make torch`, manual freeze, shared deps + link to user-guide; update `docs/contributing/.pages`
   - Prefer: fold contributor bits into `docs/contributing/development.md` (short subsection) and **delete** `docs/contributing/torch.md` to avoid a zombie page.

3. **Link cascade**
   - Files: `docs/user-guide/troubleshooting.md`, `docs/user-guide/installed-layout.md`, `docs/contributing/development.md`, `CONTRIBUTING.md`, `skills/sr-initialize/SKILL.md`, `memory-bank/techContext.md`, `memory-bank/systemPatterns.md`
   - Changes: all former `contributing/torch` → `user-guide/torch` (or development for make-torch only).

4. **Verify gates**
   - Acceptance B1–B5; `make docs-build`; `make reuse` if needed.

## Technology Validation

No new technology - validation not required

## Dependencies

- Existing Installed layout / Quickstart IA from prior rework
- Current `docs/contributing/torch.md` as content source

## Challenges & Mitigations

- **Duplicating artifact tables**: Link Installed layout; keep user-guide torch focused on contract + heal.
- **CONTRIBUTING still says “read Torch”**: Point to user-guide for contract; development for `make torch`.
- **Skill links**: Update `sr-initialize` paths so agents don’t cite a deleted contributing page.

## Pre-Mortem

- **Plan failed because contributing still owned the novel**: Step 2 deletes or hollows contributing torch; acceptance B2.
- **Plan failed because troubleshooting still sent users to contributing**: Step 3 retarget (B3).

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Pre-Mortem complete
- [x] Preflight
- [x] Build
- [x] QA
