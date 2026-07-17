---
task_id: parallel-pytest-xdist
complexity_level: 2
date: 2026-07-17
status: completed
---

# TASK ARCHIVE: parallel-pytest-xdist

## SUMMARY

Locked `pytest-xdist~=3.0` in the engine uv project and defaulted pytest to process workers via `addopts = ["-n", "auto"]` (Make/CI stay bare `pytest` and inherit it). Documented the parallel default and serial override (`-n0`) in the contributor iteration guide and `techContext`. After PR #66 / SLOBAC review, removed three vacuous hermetic contracts that grepped pytest-xdist presence and `addopts` config — supply-chain fitness tests and product wiring kept.

## REQUIREMENTS

1. Lock `pytest-xdist` in engine `dev` deps; hermetic `uv.lock`.
2. Process workers on normal pytest entrypoints via pytest `addopts` SSOT (not duplicated Make/CI flags).
3. Process isolation only; keep `STOCKROOM_HOME` / `tmp_path` safety model.
4. Safe default on heterogeneous machines (`-n auto`); document serial override.
5. **Rework:** drop low-value hermetic asserts on xdist presence/config; leave real lock fitness functions and parallel product wiring intact.

## IMPLEMENTATION

- `skills/sr-search/pyproject.toml`: `pytest-xdist~=3.0` in `[dependency-groups] dev`; `addopts = ["-n", "auto"]` under `[tool.pytest.ini_options]`.
- `skills/sr-search/uv.lock`: regenerated hermetically.
- `docs/contributing/iteration.md` + `memory-bank/techContext.md`: parallel default and `-n0` override.
- **Rework delete** from `skills/sr-search/tests/test_lock_hermetic.py`: `test_pyproject_declares_pytest_xdist_dev_dep`, `test_lock_includes_pytest_xdist`, `test_pytest_addopts_enables_xdist_auto_workers`. Remaining hermetic suite is torch-free / PyPI+hashes / override / lock-not-stale / pyproject torch contract only.

## TESTING

- Original build: full `make test` green under 16 workers (~19s; 586 pytest / 4 skipped, 86 JS).
- Rework: hermetic file 5 passed; full `make test` green (583 pytest / 4 skipped — −3 contracts); xdist still loaded via product config.
- `/niko-preflight` PASS (original); `/niko-qa` PASS (original + rework).

## LESSONS LEARNED

### Technical

- Put parallelism in pytest `addopts`, not Makefile/CI flags — one SSOT, zero workflow-file churn, ad-hoc `uv run pytest` stays parallel.
- Existing per-test warehouse isolation was enough for xdist; no serialize marks needed.
- Hermetic lock tests earn their keep as supply-chain fitness functions. Grepping pytest’s own config / xdist presence does not — green never meant “workers run,” and presence is already covered by dep pin + `uv lock --locked`.

### Process

- PR bot suggestions to *strengthen* vacuous config oracles (exact `addopts`, SpecifierSet on lock version) deepen change-detectors; prefer delete when the claim was never behavioral.

## PROCESS IMPROVEMENTS

Do not add hermetic contracts for test-runner config unless they encode a real supply-chain or architectural invariant (torch carve-out shape). Parallelism defaults belong in `pyproject.toml` + contributor docs, not in TOML greps inside the suite they configure.

## TECHNICAL IMPROVEMENTS

None for follow-up. Optional later: a one-shot behavioral probe that xdist brought up workers — only if flake or silent serial fallback becomes a real risk; not required for this ship.

## NEXT STEPS

None. Memory bank ready for the next task.
