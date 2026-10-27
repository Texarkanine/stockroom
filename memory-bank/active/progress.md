# Progress

Reclaim `warehouse.issue147-swap.duckdb` a fortnight after a recorded swap. The session-start hook stays. The process it starts returns without a child when that child would leave the disk alone, and starts a child for an unfinished migration or when that backup is due to unlink. Item 2 of issue 155 stays out.

**Complexity:** Level 3

## 2026-10-27 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - Confirmed no in-flight Niko task (no brief, tasks, progress, or milestones before this run)
    - Restated issue 154 and item 1 of issue 155; operator approved
    - Classified the combined change as Level 3
* Decisions made
    - One task, not two: the short-circuit and the unlink share the "backup still present" constraint
    - Item 2 of issue 155 is out of scope
* Insights
    - Design notes already exist at `memory-bank/active/creative/creative-swap-backup-cleanup.md` and `memory-bank/active/creative/creative-check-machinery-lifetime.md`

## 2026-10-27 - PLAN - COMPLETE

* Work completed
    - Mapped the check pass, the parent `main` path, the doctor backup name, and the restore section
    - Wrote the Level 3 plan in `memory-bank/active/tasks.md`
* Decisions made
    - No open questions. The creative decisions stand
    - The unlink is called from `_acquired` only. The parent gate does not unlink
    - `SWAP_BACKUP_FILENAME` is defined on `check` and re-exported from `doctor`
    - The DuckDB import assertion runs in a fresh interpreter
* Insights
    - `storage`, `migrate`, and `warehouse` import DuckDB, so moving the `duckdb` import line alone does not make the parent quiet

## 2026-10-27 - PREFLIGHT - COMPLETE (PASS WITH ADVISORY)

* Work completed
    - Validated implementation plan in `memory-bank/active/tasks.md` against default Level 3 preflight checks
    - Confirmed strict TDD ordering (stub tests -> stub interface -> write tests / run red -> write code / run green) across Units 1 and 2
    - Verified import boundaries, re-exports, and backward compatibility for `SWAP_BACKUP_FILENAME`
    - Formulated advisory recommendations for module globals in `check.py` and pre-deadline child-spawn suppression
* Decisions made
    - Plan validated as `PASS WITH ADVISORY`
    - Implementation plan proceeds to Build without structural blockers
* Insights
    - Parent gate can cleanly avoid importing DuckDB while keeping all child background machinery working as intended

## 2026-10-27 - PLAN - IN-PROGRESS

* Work completed
    - Operator recalled the plan and chose the quiet-parent gate
    - Retired the preflight status that passed the coarser rule
* Decisions made
    - The session-start hook text stays
    - The parent returns without a child when that child would leave the disk alone
    - The child still starts for an unfinished migration and when a swapped backup is due to unlink
* Insights
    - A present backup is not by itself a reason to start the child. The unlink predicate is

## 2026-10-27 - PLAN - COMPLETE

* Work completed
    - Revised the Level 3 plan, the brief, and the check-lifetime design note to the operator's gate
    - The parent calls `launch()` for an unfinished version-1 home, and for a swapped backup whose fortnight has elapsed and whose inode differs
    - The parent returns when the child would leave the disk alone, including a young swapped backup
* Decisions made
    - The hook files are not edited
    - The unlink stays in `_acquired`. The parent does not unlink
    - `WAREHOUSE_FILENAME` and `SWAP_BACKUP_FILENAME` move to `stockroom.home`, which stays stdlib-only
    - The due child may still import DuckDB. The flock stays on `warehouse`
* Insights
    - Matching inodes have to be part of the parent gate. A clock-only gate would launch forever, because the child would keep the file

## 2026-10-27 - PREFLIGHT - COMPLETE (PASS WITH ADVISORY)

* Work completed
    - Validated the revised Level 3 plan against the default preflight checks, tracing every touched constant and import through the live codebase
    - Confirmed strict TDD ordering in Units 1 and 2, the re-export convention for the moved filenames, and that existing stop-path tests stay green under the reclaim
    - Verified `stockroom/__init__.py` is import-light, so the fresh-interpreter DuckDB assertion is meaningful, and that no reader of `check.json` exists outside `check`/`doctor`/tests
* Decisions made
    - Plan validated as `PASS WITH ADVISORY`; no blocking findings; no in-phase plan edits (no strikes, no step swaps)
* Insights
    - The parent's due-predicate and the child's unlink predicate are stated twice in the plan; one shared `_swap_backup_due` helper would make drift between gate and reclaim impossible
    - The parent's flock-free stat path can race a concurrent due child; treating `OSError` from the stat calls as "start the child" closes it, per the plan's own Challenges principle

## 2026-10-27 - BUILD - IN-PROGRESS

* Work completed
    - Entered build. The preflight checkpoint was already `3d74def`
* Decisions made
    - One `_swap_backup_due` owns the predicate. `_reclaim_swap_backup` unlinks only when it is true. `_needs_child` launches when it is true
    - `OSError` from that predicate starts the child and does not unlink
    - `test_expired_start_deletes_a_leftover_and_keeps_the_backup` keeps its backup at a fortnight, instead of a second expired-start test
    - `docs/architecture/lifecycle.md` gets one sentence: a finished home with nothing due starts no child
* Insights
    - The shared predicate must let `OSError` propagate. Swallowing it as "not due" would skip the reclaim session the advisory is closing

## 2026-10-27 - BUILD - COMPLETE

* Work completed
    - Unlink a swapped backup 14 days after `started_at` when the inodes differ, under the writer flock, without rewriting `check.json`
    - The parent returns without a child and without DuckDB when that child would leave the disk alone, and launches for an unfinished home or a due backup
    - Moved the two filenames to `stockroom.home` and re-exported them
    - Updated the restore section and one sentence in the lifecycle doc
* Decisions made
    - `_swap_backup_due` is the only predicate. The parent maps `OSError` to launch. The unlink leaves the backup when that call raises
    - The user guide says 14 days
    - The expired-start test keeps a fortnight-old backup instead of a second test
* Insights
    - Placeholders at import, rebound by `_import_engine` inside `run_check`, keep DuckDB off the parent
    - `make test` on this machine needs Node 22 from nvm. Brew `node` is 26 and the dashboard target rejects it
    - Two suite failures are outside this change: `/tmp` resolves to `/private/tmp` in the dashboard identity round trip, and the root docs lock fails `uv lock --locked --refresh`


## 2026-10-27 - QA - COMPLETE (PASS)

* Work completed
    - Reviewed the build diff against the Level 3 plan for KISS, DRY, YAGNI, completeness, regressions, leftover scaffolding, and docs
    - Targeted suites: 121 passed, 1 skipped. Ruff check and format: clean
* Decisions made
    - PASS. Nothing blocks acceptance
    - Optional fixes: a loose pointer comment in `test_check.py`, and the restore steps could warn that a session after the 14 days can remove the backup
* Insights
    - Every runtime use of the placeholder engine names is reached only through `run_check`. That is what keeps DuckDB off the parent path

## 2026-10-27 - REFLECT - COMPLETE

* Work completed
    - Compared the brief, the revised plan, both creative decisions, the build, and the QA pass
    - Wrote `memory-bank/active/reflection/reflection-fortnight-backup-and-quiet-check.md`
    - Persistent files: productContext, systemPatterns, and techContext stay. None of them stated a contract this change broke. The home module was already the stdlib path layer. The hook still starts the check command on session start.
* Decisions made
    - QA's two notes stay optional. Applying them would reopen a pass that already succeeded
* Insights
    - The shared due-predicate has to raise `OSError`. The parent and the unlink want opposite answers, and the helper cannot pick one
    - The first preflight had approved a gate the operator then removed. Retiring that status avoided building it
