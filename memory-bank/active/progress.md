# Progress

Enable safe process-level parallel pytest for the stockroom engine suite via locked pytest-xdist, wired into Make and CI.

**Complexity:** Level 2

## 2026-07-17 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - Intent clarified and approved: parallel Python testing with process workers, safely
    - Complexity classified as Level 2
* Decisions made
    - Scope is pytest-xdist + make/CI wiring; threaded parallelism out of scope
    - Dashboard JS suite out of scope
* Insights
    - Existing `warehouse_home` / `tmp_path` isolation already matches xdist’s process model

## 2026-07-17 - PLAN - COMPLETE

* Work completed
    - TDD plan: lock/hermetic contracts for xdist + `addopts -n auto`, then full parallel suite gate
    - Technology PoC: `pytest-xdist==3.8.0` install + `-n 2` smoke (6 passed); reverted for clean build TDD
* Decisions made
    - pytest `addopts = -n auto` is SSOT (Make/CI stay bare `pytest`)
    - Extend `test_lock_hermetic.py` rather than a new test module
    - Serial debug path documented as `pytest -n0`
* Insights
    - Dashboard JS parallelism and Make-level JS∥pytest overlap remain explicitly out of scope
