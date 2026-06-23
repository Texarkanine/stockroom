# Project Brief

## User Story

As the operator building stockroom, I want **Phase 0 — Foundations** of the roadmap in place — a dual-manifest plugin skeleton, a hermetically locked uv project that holds torch out of the lock, release-please versioning, and a test/lint/format harness — so that every later phase is built on a trustworthy, reproducible, test-first substrate rather than inventing its footing under pressure.

## Use-Case(s)

### Use-Case 1: Trustworthy substrate

A contributor clones the repo fresh and reconstructs the exact, hash-verified dependency environment from the committed lock — entirely from PyPI, with no torch and no ambient-config leakage — proving the supply-chain promise before any product code exists.

### Use-Case 2: Dual-harness packaging from day one

The committed layout *is* the install layout for both Cursor and Claude Code (two manifests, one shared `skills/` tree, no build step), so all later phases are exercised against both harnesses, and release-please can cut a version that syncs into both manifests in lockstep.

### Use-Case 3: Test-first from line one

The test/lint/format harness is stood up with one trivial green test, so the very first line of real code in Phase 1 is written test-first.

## Requirements

1. **Dual-manifest plugin scaffold** — `.cursor-plugin/plugin.json` and `.claude-plugin/plugin.json` over a shared `skills/` tree; AGPLv3 confirmed in place; committed-layout-equals-install-layout (no build step); both manifests ship from the start.
2. **release-please wired** — `release-please-config.json` and its manifest configured to version stockroom and sync that version into both plugin manifests in lockstep.
3. **Locked uv project skeleton** inside the app-bearing skill directory — `pyproject.toml` (with `requires-python` and the torch-exclusion override) plus a hermetic `uv.lock` produced by `uv lock --no-config`; the torch-safe run contract (`uv run --no-sync` / `--inexact`, never an exact sync) documented as the standard invocation.
4. **Test, lint, and format harness** — the test framework configured in `pyproject.toml` with one trivial green test, plus a formatter and a linter.

## Constraints

1. **No product code yet** — Phase 0 builds substrate only; it must end with zero product behavior.
2. **uv-locked except torch** — everything pinned and hash-verified through `uv.lock`; torch excluded from the lock via the proven impossible-marker override; lock generated hermetically with `uv lock --no-config`.
3. **AGPLv3** — already in the repo; confirmed, not re-litigated.
4. **Both manifests from the start** — no single-harness phase.
5. **No build step** — committed layout = install layout.
6. **Clean-room** — w.r.t. `claude-warehouse` (no bearing on Phase 0 content, but the posture holds).

## Acceptance Criteria

1. A fresh clone resolves the locked environment hermetically — entirely from PyPI, with hashes, no ambient-config leakage, and no torch/CUDA/nvidia entries in the lock.
2. The test suite runs green on one trivial test; the formatter and linter run clean.
3. Both plugin manifests validate.
4. release-please can cut a versioned release on demand, syncing the version into both manifests.
5. No product code exists yet.
