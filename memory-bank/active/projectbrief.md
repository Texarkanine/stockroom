# Project Brief

## User Story

As a stockroom contributor, I want the engine pytest suite to run with safe process-level parallelism so that full verification finishes faster without flaky shared-state failures.

## Use-Case(s)

### Use-Case 1: Local full suite

Run `make test` (or the engine pytest invocation it wraps) and get process-worker parallel Python tests by default.

### Use-Case 2: CI full suite

CI’s pytest step uses the same parallel worker model so PR gates benefit from the same speedup.

## Requirements

1. Add a locked process-worker parallel runner for pytest (`pytest-xdist`) to the engine uv project’s `dev` dependency group; regenerate/update `uv.lock` hermetically.
2. Wire parallel workers into the normal pytest entrypoints: root `Makefile` `test` target and `.github/workflows/ci.yml` Test step (and `test-dashboard-py` if it should stay consistent).
3. Prefer process isolation only — do not introduce threaded/shared-process pytest parallelism.
4. Keep per-test warehouse isolation (`STOCKROOM_HOME` / `tmp_path`) as the safety model; fix any isolation gaps that parallel workers expose.
5. Choose a worker policy that is safe on heterogeneous machines (including WSL) — e.g. `-n auto` or a modest capped default — and document it where contributors already look for test commands.

## Constraints

1. Supply-chain posture: pin via committed `uv.lock`; no unpinned ad-hoc installs.
2. Torch-safe invocation flags remain (`--no-sync` / `--no-config` as today).
3. TDD for any code/test-isolation fixes required to make parallel runs green.
4. Dashboard JS tests are out of scope unless a trivial Make sequencing tweak is needed; this task is Python pytest parallelism.

## Acceptance Criteria

1. `pytest-xdist` is a locked `dev` dependency of `skills/sr-search`.
2. `make test` and CI run pytest with process workers (documented flag/policy).
3. Full engine pytest suite passes under that parallel configuration (including warehouse concurrency and dashboard server tests).
4. Contributor-facing test docs mention the parallel default if they currently document the pytest command.

## Rework

### Trigger

PR #66 review + SLOBAC triage: hermetic contracts that only assert pytest-xdist presence / pytest `addopts` config add no supply-chain value and are vacuous proxies for “workers run.”

### Rework Goals

1. Remove low-value hermetic tests for pytest-xdist presence and config from `skills/sr-search/tests/test_lock_hermetic.py` (at minimum: dep-declaration / lock-includes-xdist / addopts `-n auto` contracts added in the original build).
2. Leave real hermetic fitness functions intact (torch/CUDA leak, PyPI+hashes, torch override, lock not stale, pyproject torch contract).
3. Leave product wiring intact: locked `pytest-xdist`, `addopts = ["-n", "auto"]`, contributor docs — this rework is delete-smelly-tests, not undo-parallelism.
4. Suite stays green under parallel `make test`.
