---
task_id: p0-foundations
date: 2026-06-22
complexity_level: 3
---

# Reflection: Phase 0 — Foundations

## Summary

Stood up the full stockroom substrate — a locked, torch-free uv engine inside `skills/sr-search/`, dual Cursor/Claude-Code plugin manifests over a shared `skills/` tree, release-please versioning, enforced layered REUSE licensing, and a pytest/ruff/reuse harness with CI — test-first and with zero product behavior. Succeeded: 17 tests green, lint/format/lock-locked clean, `reuse lint` compliant across the whole tree.

## Requirements vs Outcome

Every Project-Brief requirement and acceptance criterion was delivered:

- Dual-manifest scaffold, no build step, AGPL confirmed ✓
- release-please wired to sync one version into both manifests in lockstep ✓
- Locked uv project with the torch-exclusion override + hermetic lock ✓
- Test/lint/format harness with green tests ✓
- No product code ✓

One acceptance criterion ("release-please can cut a release on demand") was — per the plan and operator confirmation — satisfied as *config-valid + workflow-present + lockstep-tested*, with the live release flip owned by the operator post-merge and the end-to-end proof deferred to Phase 5. Nothing was dropped or silently descoped.

## Plan Accuracy

The plan was unusually accurate — the 6-step sequence held exactly, file lists matched, and the `slobac` template + o9-torch spike meant the riskiest mechanism (hermetic torch-free lock) was a known quantity going in. Two small surprises, both in-scope:

- **`.gitignore` had to move from step 6 to step 1** — you cannot make a clean commit at the end of step 1 without first ignoring `.venv/`/`__pycache__/`. The plan's ordering was an artifact of grouping "polish" items together; in practice the ignore file is a step-1 prerequisite.
- **Step 2's TDD red could not be staged the way the plan implied.** "Write the lock test (fails — no lock) → generate lock → pass" can't literally run, because a lock must exist to bootstrap the interpreter that runs *any* test. The red was real but had to be staged by moving an already-bootstrapped lock aside.

The identified challenges (REUSE precedence ordering, whole-tree `reuse lint` coverage, non-package uv project, ambient-config leakage) all materialized exactly as anticipated and the planned mitigations worked first try.

## Creative Phase Review

No creative phase was executed — all open questions were resolved at high confidence during planning (engine host, skeleton-skill convention, uv shape, licensing model). This held up: nothing during build revealed a decision that needed creative re-exploration. The decision to skip creative was correct.

## Build & QA Observations

Build was smooth and largely friction-free, which is attributable to the reference materials (`slobac` for manifests/release-please/REUSE; the o9 spike for the lock). Each step's red→green cycle was crisp. QA found exactly one issue — a documentation-accretion debt: `techContext.md` had promised to point at the Phase 0 canonical artifacts once they existed, and they now did. Mechanical checks (lint/test/reuse) could never have caught that; it's precisely the semantic gap QA exists for.

## Cross-Phase Analysis

- **Preflight earned its keep.** It promoted REUSE from advisory to enforced and added the `uv lock --locked` staleness guard — both shipped as first-class, tested artifacts rather than being discovered as gaps mid-build.
- **Planning thoroughness → build calm.** Because the plan pinned the repo layout and the PLUGIN_ROOT pattern into `systemPatterns.md`, build never had to re-derive architecture; it was pure execution.
- **The one QA finding traces to a planning omission**, not a build error: the plan listed updating persistent memory-bank pointers nowhere, so build legitimately didn't do it, and QA caught the consequence. Cheap to fix, but a reminder that "update the docs that point at what you just built" belongs in the plan's final step.

## Insights

### Technical

- **A locked-project's first test run is a bootstrap paradox for TDD.** When the lockfile *is* one of the artifacts under test, you can't have a "no lock" red and a runnable test interpreter at the same time. Stage the red by moving an existing lock aside — and write lock-assertions to read/parse files (not import the env) so they're robust to this.
- **`uv lock --no-config` is load-bearing for hermeticity and is worth a standing CI guard.** The combination of the impossible-marker torch override + `--no-config` reproduced the spike's result in-place (51 packages vs the spike's 38, the delta being the dev group), zero torch/CUDA/nvidia, all PyPI+hashed.
- **REUSE's last-match-wins ordering cleanly expresses "AGPL code inside a PPL-S skill dir"** — base `**/*`→AGPL, `skills/**`→PPL-S, then code-shaped `skills/**` globs→AGPL again. `reuse spdx` (tag-value) is a reliable way to *test* per-file resolution, not just whole-tree compliance.

### Process

- **"Reconcile the docs that point at the artifacts you just created" should be an explicit build step, not left to QA.** The single QA finding was a persistent-file pointer that the plan never scheduled an update for. Folding a "update memory-bank pointers to new canonical artifacts" item into the final build step would have made QA fully clean.
- **For substrate/config tasks, the plan's TDD cycle boundaries are aspirational, not literal.** Bootstrap order (ignore-file first, lockfile-before-interpreter) overrides the tidy "one failing test → one artifact" framing. This is fine — the spirit (tests written and observed failing first) was honored — but future config-phase plans should expect to re-order for bootstrap reality.
