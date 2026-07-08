---
task_id: p3-m3-sr-initialize-torch-cli
date: 2026-07-08
complexity_level: 3
---

# Reflection: p3-m3-sr-initialize-torch-cli

## Summary

Built the onboarding half of `sr-initialize`: a read-only `stockroom doctor` module (torch-free `probe` facts + loud-failing `smoke` through the real encoder path), the dispatcher's seventh subcommand, and the `skills/sr-initialize/SKILL.md` prose skill — validated live on both the Linux/CUDA and CPU paths with `make ci` green. Succeeded, built to plan, QA clean.

## Requirements vs Outcome

Every m3 requirement delivered: uv prerequisite check, platform/accelerator detection, human-confirmed out-of-band torch provisioning, the ratcheted smoke test (version, `cuda.is_available()`, one real encode), and m2 shim binding — plus the operator-gate amendments (errmsg ratchet, self-managed-torch branch, idempotent re-entry, dev-checkout deferral to `make shim`). Nothing dropped or reinterpreted. One unplanned addition earned its place: `probe` reports `gpu-compute-cap` (the `sm_` generation fact the wheel-choice guidance explicitly needs — the plan's guidance mentioned the caveat but the fact list hadn't named the field).

## Plan Accuracy

The six-step sequence, file list, and 16-behavior test plan were executed exactly as written — no reordering, no scope changes. Both surprises were *environmental*, not structural:

- `uv pip install --project` does not discover the engine venv (fails with "No virtual environment found" unless cwd is the project); the working form is `--directory`. The plan's remedy string assumed `--project` worked because `uv run --project` does — the two subsystems resolve differently.
- `make shim` (m2's dev parity target) baked *relative* paths into the shim: `uv --directory` moves the cwd before the module runs, so `--app-dir skills/sr-search` rendered a shim whose baked dir was dead from anywhere but the checkout root. Pre-existing bug, invisible until this task actually exercised the installed dev shim.

The anticipated challenges (torch-free CI vs torch-dependent smoke, nvidia-smi variance, wrong-wheel ugliness) all materialized and were all covered by the planned mitigations.

## Creative Phase Review

Option C (read-only doctor + prose orchestration) held up without a single friction point. The facts/judgment boundary was never ambiguous during build: every "should this go in Python?" question answered itself by asking "is it a fact or a choice?". The two-command split also made the live validation naturally incremental — probe was verifiable before torch existed, smoke immediately after. The never-do list from the creative exploration functioned as a live checklist during SKILL.md authoring (the guarded sync in step 3 exists directly because of never-do #1).

## Build & QA Observations

Build was smooth: three clean red→green cycles, no test rework, no plan-deficiency stops. The one iterative loop was remedy wording (the `--project`→`--directory` fix rippled into B8's assertion — exactly what "tests assert remedy content" was for; the ratchet test caught that the printed command must actually work). QA found nothing substantive — the preflight + operator-gate amendments had already squeezed the ambiguity out before code was written.

## Cross-Phase Analysis

- The operator's gate-review amendments (errmsg ratchet, self-managed branch) directly shaped B8–B10's assertions and the SKILL.md's step 5/6 structure — a cheap plan-phase intervention that would have been a QA finding otherwise.
- The project invariant "execute every example live before writing it in" is what surfaced both environmental bugs; the unit suite could not have caught either (both live in uv's CLI behavior, outside any injectable seam). Cause → effect: prose-with-live-verification acted as the integration test layer the pytest suite deliberately doesn't own.
- Preflight's verification that `stockroom.embed` imports torch-free is what made the module-top `from stockroom.embed import BgeEncoder` safe without a lazy-import dance (B7 pinned it anyway).

## Insights

### Technical

- **`uv pip` and `uv run` resolve projects differently**: `uv run --project X` works from anywhere, but `uv pip install --project X` requires the venv to be discoverable from the *cwd* — use `--directory X` for pip operations against a non-cwd project. Any future rendered command that targets the engine venv must use the `--directory` form.
- **`uv --directory` moves the cwd before argv is interpreted** — every path handed to a module through that form must be pre-absolutized (`$(CURDIR)` in make). Relative paths that "work when you test from the repo root" are the trap shape.
- The B14/B12 complement pattern (a subprocess failure test that self-skips when the dependency is present, paired with an `importorskip` success test) means every environment runs exactly one of the pair — a reusable shape for any dependency-gated loud-failure contract.

### Process

- Live-verifying prose examples before committing them is not a formality: it caught two real bugs this task (a dead remedy command and a dead dev shim), both outside the unit suite's reach. The invariant pays for itself precisely at the seams injection can't cover.
- Asserting remedy *content* (not just exit codes) in failure-path tests turned a wording fix into a test-caught contract change — the errmsg ratchet is self-enforcing once encoded in tests.
