# Progress

Teach the nightly job to run `stockroom shim ensure-env` before ingest, so a missing torch is healed on an unattended night and a failed heal still lets ingest run. Spec: [issue #146](https://github.com/Texarkanine/stockroom/issues/146).

**Complexity:** Level 1

## 2026-10-20 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - Confirmed the task is issue #146 as written, with #147 left out
    - Wrote the project brief from that issue
* Decisions made
    - Level 1: one bug, one owner (`render_payload`), and the shell string is already specified
* Insights
    - `cold-storage` already holds the #147 creative commits, including `memory-bank/active/creative/creative-warehouse-footprint.md`. This task branches from `origin/main` so that file stays on `cold-storage`.

## 2026-10-20 - BUILD - COMPLETE

* Work completed
    - Taught `render_payload` to run `stockroom shim ensure-env` before ingest, with ingest still gated on `&&` before embed
    - Covered the new payload, odd log paths, failure grouping, and stale-entry status in `tests/test_schedule.py`
    - Updated the schedule help text and the docs that quoted the old nightly command
    - `make ci` passed (1024 pytest, 134 dashboard JS, lint, format, REUSE)
* Decisions made
    - The in-scope quote in the log-path test is `'`, the same character the existing scheduler tests already require
* Insights
    - Status did not need a new comparison. It already re-renders the current payload and diffs the installed entry against that.
