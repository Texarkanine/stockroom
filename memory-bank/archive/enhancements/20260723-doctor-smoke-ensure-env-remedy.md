---
task_id: doctor-smoke-ensure-env-remedy
complexity_level: 2
date: 2026-07-23
status: completed
---

# TASK ARCHIVE: doctor-smoke-ensure-env-remedy

## SUMMARY

Implemented [#86](https://github.com/Texarkanine/stockroom/issues/86) on `feat/doctor-smoke-ensure-env-remedy` / PR [#88](https://github.com/Texarkanine/stockroom/pull/88): when `stockroom doctor smoke` fails because torch is missing, recommend `stockroom shim ensure-env` if `torch_source.read_freeze_path()` finds a usable hashed freeze; otherwise keep the existing `uv pip install torch …` / `sr-initialize` remedy. Post-PR rework isolated CLI smoke from ambient `STOCKROOM_HOME` with two explicit subprocess cases (empty home → pip; usable freeze → ensure-env).

## REQUIREMENTS

1. Freeze present + missing torch → smoke recommends `stockroom shim ensure-env` (optionally still mention `sr-initialize` as re-pick).
2. No freeze → keep pip / `sr-initialize` guidance.
3. Scope: smoke errmsg ratchet + tests; align with `docs/user-guide/troubleshooting/torch.md`; do not redesign provisioning.

**Acceptance (all met):** freeze-aware unit + CLI coverage; no-freeze path unchanged; torch.md doctor-smoke bullet.

## IMPLEMENTATION

1. `run_smoke` missing-torch branch calls `read_freeze_path()` (same usability gate as `ensure_torch` / heal).
2. Freeze present → remedy names `stockroom shim ensure-env` (+ optional `sr-initialize` re-pick); no raw `uv pip install torch`.
3. No / unusable freeze → existing pip `--directory` remedy.
4. Unit tests under isolated `STOCKROOM_HOME`: no-freeze, usable-freeze, unusable-freeze.
5. CLI: `_run` accepts env overrides; empty home + freeze-written home cases (no ambient branching).
6. Docs: doctor-smoke missing-torch bullet in `torch.md`.

| Area | Files |
|------|--------|
| Doctor | `skills/sr-search/src/stockroom/doctor.py` |
| Tests | `skills/sr-search/tests/test_doctor.py`, `test_doctor_cli.py` |
| Docs | `docs/user-guide/troubleshooting/torch.md` |

## TESTING

- TDD: freeze-present unit case failed first; then implementation green.
- `/niko-preflight` PASS (amended CLI step into test-before-code order); `/niko-qa` PASS.
- Final verify: `make format && make lint && make test` — **672 passed, 4 skipped**.

## LESSONS LEARNED

### Technical

- Smoke remedies should gate on the same freeze usability predicate as heal (`read_freeze_path`), not a looser "files exist" check.
- Env-adaptive CLI assertions on real home are weak; pin `STOCKROOM_HOME` in the subprocess and cover both remediations explicitly — subprocess coverage still matters because it proves home env reaches the child.

### Process

- Nothing notable beyond preflight catching TDD ordering (CLI test update belonged before production code).

### Million-dollar question

If freeze-aware remedies had been assumed from the start, doctor would expose a tiny shared "next action for missing torch" helper. The inlined branch at one call site is the natural minimal form; extracting a helper now would be premature.

## PROCESS IMPROVEMENTS

None — L2 plan → preflight → build → QA → reflect held.

## TECHNICAL IMPROVEMENTS

None required for this change. Optional later: extract `_missing_torch_remedy(app_dir)` if a second call site appears.

## NEXT STEPS

None for this task. Merge PR [#88](https://github.com/Texarkanine/stockroom/pull/88) when ready.
