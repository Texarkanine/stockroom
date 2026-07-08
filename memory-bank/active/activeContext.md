# Active Context

## Current Task: p3-m3-sr-initialize-torch-cli
**Phase:** REFLECT - COMPLETE (QA PASS, reflection written)

## What Was Done
- All six plan steps executed in order, TDD red→green for every Python step:
    - `skills/sr-search/src/stockroom/doctor.py` (new): `probe_facts`/`format_facts` (torch-free facts, injectable `smi_runner`/`torch_importer`, every nvidia-smi failure degrades to a fact) + `run_smoke` (ratcheted one-line failures, real `BgeEncoder` default) + flat `probe|smoke` CLI
    - `stockroom.__main__.SUBCOMMANDS`: seventh row `doctor`
    - New `tests/test_doctor.py` (16 tests, B1–B12) and `tests/test_doctor_cli.py` (3 tests, B13–B15); `tests/test_dispatcher_cli.py` extended (B16: tuple + `doctor`→`probe` fingerprint)
    - `skills/sr-initialize/SKILL.md` (new): 7-step onboarding prose — every example executed live on this machine before being written in
    - Docs: README (`doctor` in the subcommand list + `sr-initialize` onboarding pointer), techContext (doctor + sr-initialize sections), systemPatterns (onboarding application of the judgment-vs-mechanism split)
- Live validation: Linux/CUDA path green (`stockroom doctor smoke` exit 0, cuda True, real encode; B12 un-skipped 16/16); CPU path green (`CUDA_VISIBLE_DEVICES="" … doctor smoke` exit 0, cuda False); shim ownership-refusal relay, idempotent re-install, guarded re-entry sync, and the torch-stripping sync hazard all observed live
- `make ci` green end to end (pytest 329 passed/3 skipped torch-free shape, ruff check/format, lock-check, REUSE 194/194)

## Key Implementation Decisions (build-time)
- **Smoke remedy uses `--directory`, not `--project`**: `uv pip install --project` fails with "No virtual environment found" unless cwd is the project (verified live); the ratchet line and B8 assert `--directory <engine>` so the printed command actually works from anywhere
- `probe` reports `gpu-compute-cap` (from `nvidia-smi --query-gpu=compute_cap` CSV) — the `sm_` generation fact the wheel-choice guidance needs — and `driver-cuda` parsed from the `nvidia-smi --version` banner (the CSV query set has no cuda_version field)
- B14 (subprocess torch-free smoke) skips itself when torch is importable (complement of the `importorskip` real-model test, so both dev boxes and CI run exactly one of the pair)
- `make shim` fixed to bake absolute paths (`$(CURDIR)`): `uv --directory` moves the cwd, so the previous relative `--app-dir`/`PYTHONPATH` rendered a dead shim — found live, fix committed with the build

## Deviations from Plan
- None structural. Two in-flight corrections: the `--project`→`--directory` remedy fix (plan assumed `--project` worked) and the pre-existing `make shim` relative-path bug (surfaced by live validation; fixing it was required to validate the dev-shim path)

## Reflection Outcome
- `reflection-p3-m3-sr-initialize-torch-cli.md` written: built to plan (6/6 steps, QA clean); both surprises were environmental uv behaviors caught by the live-example invariant (`uv pip` needs `--directory` not `--project`; `uv --directory` moves the cwd → `make shim` relative-path bug); persistent files already reconciled during the docs step

## Next Step
- L4 sub-run: operator runs `/niko` to advance to the next milestone (m4 — scheduling and first run)
