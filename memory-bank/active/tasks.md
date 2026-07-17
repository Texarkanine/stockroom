# Task: parallel-pytest-xdist (rework)

* Task ID: parallel-pytest-xdist
* Complexity: Level 1
* Type: quick fix (remove vacuous hermetic contracts)

## What broke / smelled

Three hermetic contracts asserted pytest-xdist *presence* and pytest `addopts` *config* by grepping committed TOML/lock bytes. They never verified workers run, duplicated dep pin + `uv lock --locked`, and were vacuous change-detectors on test-runner config.

## Fix

Deleted from `skills/sr-search/tests/test_lock_hermetic.py`:

- `test_pyproject_declares_pytest_xdist_dev_dep`
- `test_lock_includes_pytest_xdist`
- `test_pytest_addopts_enables_xdist_auto_workers`

## Kept

- Supply-chain hermetic suite (torch-free, PyPI+hashes, override, lock not stale, pyproject torch contract)
- Product wiring: locked `pytest-xdist`, `addopts = ["-n", "auto"]`, contributor docs

## Verification

- `tests/test_lock_hermetic.py`: 5 passed
- `make test`: 86 JS + 583 pytest / 4 skipped (was 586; −3 contracts)

## QA — PASS

- KISS/YAGNI: delete only; no replacement meta-tests
- Completeness: rework goals met; product xdist wiring untouched
- Regression: hermetic fitness functions + parallel suite intact
