# Progress

The 14-day backup soak starts when the new warehouse is the live file. Phase B `started_at` stays the alarm clock. The backup is unlinked only when the soak time is at least 14 days old.

**Complexity:** Level 2

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

## 2026-10-28 - REWORK - IN-PROGRESS

* Work completed
    - Operator chose rework over archive on the completed fortnight-backup task
* Decisions made
    - The 14-day clock starts when the new warehouse is the live file, not at phase B `started_at`
    - PR 156: dismiss the `tasks.md` comment because `memory-bank/active/` is archived before merge
    - PR 156: dismiss boolean `check_version` and non-finite `started_at`
* Insights
    - A `linked` record can sit indefinitely, and `_finish_swap` keeps the original `started_at`, so the backup can be removed on the session after the one that writes `swapped`

## 2026-10-28 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - Classified the soak-clock rework as Level 2
* Decisions made
    - One subsystem: the check pass, its tests, and the user-guide sentences. A second timestamp on the existing record. `started_at` stays the alarm clock.
* Insights
    - Level 1 is too small: both write sites and the predicate have to agree. Level 3 is too big: this does not add a component or change the check's shape.

## 2026-10-28 - PLAN - COMPLETE

* Work completed
    - Wrote the Level 2 plan in `memory-bank/active/tasks.md`
* Decisions made
    - `swapped_at` is the soak clock, stamped when status becomes `swapped`
    - A swapped record with no `swapped_at` is stamped on the stop path and kept 14 days from that stamp
    - `started_at` is not a fallback clock
* Insights
    - The parent has to launch when the stamp is missing, or the child never writes it

## 2026-10-28 - PREFLIGHT - COMPLETE (FAIL (fixable))

* Work completed
    - Validated the Level 2 soak-clock plan against the default preflight checks and the live `check.py` and `test_check.py`
    - TDD ordering, conventions, and dependency impact pass. No strikes or step swaps
* Decisions made
    - FAIL (fixable). Five existing tests go red under the stamp or the new parent launch, and the plan does not list them
    - The unconditional parent launch on a missing `swapped_at` contradicts AC 7 and AC 12 of the brief
* Insights
    - Gating the missing-stamp launch on a present backup keeps finished homes quiet. One `_mark_swapped` writer would keep every `swapped` write carrying the soak clock

## 2026-10-28 - PLAN - COMPLETE

* Work completed
    - Revised the plan for the fixable preflight
* Decisions made
    - Stamp and launch for a missing `swapped_at` only when both files exist and the inodes differ
    - Acceptance criteria 7 and 12 stay. The Rework section replaces the `started_at` clock clauses
    - `_stamp_swapped_at` writes through `_write_outcome` and returns `None`
    - One `_mark_swapped` writer stays out of this rework
* Insights
    - `run_check` on a swapped home with no backup must not rewrite `check.json`, because those tests call the child directly

## 2026-10-28 - PLAN - COMPLETE

* Work completed
    - Added the landed-replace resume to the plan after the second fixable preflight
* Decisions made
    - `test_replace_that_lands_resumes_without_copying` resumes 15 days later and expects `swapped_at` from that clock
    - `OSError` on the new file check starts the child and leaves the record on the stop path
    - Use-cases 1, 3, and 4 join the brief clauses this rework replaces
* Insights
    - The failed-replace resume does not exercise the branch where the new warehouse is already live

## 2026-10-28 - PREFLIGHT - COMPLETE (FAIL (fixable))

* Work completed
    - Re-validated the revised Level 2 plan against the default preflight checks, the live `check.py`, and `test_check.py`
    - Both earlier findings are fixed. The file-gated stamp keeps every named existing test green, and AC 7 and AC 12 hold
    - TDD ordering, conventions, and dependency impact pass. No strikes or step swaps
* Decisions made
    - FAIL (fixable). Rework item 5 (the replace landed and the `swapped` write was delayed) has no test. The only resume test covers the failed-replace branch of `_finish_swap`
* Insights
    - `_finish_swap` has two `swapped` writes, and each one needs its own resume test at a later clock
    - One tri-state `keep` / `stamp` / `unlink` predicate would let the parent gate and the child share the distinct-files check

## 2026-10-28 - PREFLIGHT - COMPLETE (PASS WITH ADVISORY)

* Work completed
    - Re-validated the revised Level 2 plan against the default preflight checks, the live `check.py`, and `test_check.py`
    - The landed-replace resume now reads `swapped_at`, so both `swapped` writes in `_finish_swap` have a test. Earlier advisories are applied
    - Traced every existing `swapped` and `linked` test. None goes red without being named in the plan. No strikes or step swaps
* Decisions made
    - PASS WITH ADVISORY. The first line of `.preflight-status` is `PASS WITH ADVISORY`
    - Advisories: name the `started_at` the retargeted deadline fixture carries, update the module and `main` docstrings, rewrite the missing-`started_at` test instead of adding one, and drop the unused `_outcome` parameter
* Insights
    - A deadline fixture with `started_at` equal to `swapped_at` passes before the change. The old-clock test is the one that guards Unit 1

## 2026-10-28 - BUILD - COMPLETE

* Work completed
    - Unlink reads `swapped_at`. Phase B and both `_finish_swap` writes stamp it from the injected clock
    - A missing or `None` `swapped_at` is stamped on the stop path only when the backup and the live warehouse are different files, and that pass returns before the unlink
    - The user guide measures the 14 days from when the new warehouse is the one in use
    - `tests/test_check.py`: 82 passed. Engine pytest: 1232 passed, 6 skipped, 5 failed outside this change (dashboard `/tmp` vs `/private/tmp`, stale root docs lock, and three Node 26 coverage tests). Those three pass with Node 22. Dashboard JS: 134 passed under Node 22. Ruff check and format are clean
* Decisions made
    - Deadline fixtures use a young `started_at` so the old predicate fails the new assertions
    - The failed-replace 15-day resume is the second pass of the existing test
    - `_distinct_backup` is shared by the parent and the stop path. The `keep` / `stamp` / `unlink` function stays out
* Insights
    - A frozen phase B clock makes `started_at` and `swapped_at` equal. Only the later resume clock shows the gap

## 2026-10-28 - QA - COMPLETE (FAIL)

* Work completed
    - Reviewed `4503ab5..c07a81c` against the Level 2 soak-clock plan for KISS, DRY, YAGNI, completeness, regressions, leftover scaffolding, and docs
    - `tests/test_check.py`: 82 passed. Ruff check and format: clean
* Decisions made
    - FAIL (fixable). Build reruns. `test_parent_missing_started_at_returns` asserts a launch, and its name says the parent returns. It and three other retargeted tests still name `started_at` when the body tests `swapped_at`
    - Advisories: the unused `_outcome` `swapped_at` parameter, an unwrapped module docstring line, and the lifecycle sentence that misses the one stamp child
* Insights
    - When a test is retargeted, its name is part of the change. The plan said to retarget these tests and did not say to rename them

## 2026-10-28 - BUILD - COMPLETE

* Work completed
    - Renamed the four tests so each name states `swapped_at` and the assertion
    - Dropped the unused `swapped_at` parameter on `_outcome`. The record still stores `None`
    - Reflowed the module docstring. The lifecycle sentence now includes the one stamp child
    - `tests/test_check.py` passed after the rename. Ruff check and format are clean
* Decisions made
    - `_stamp_swapped_at` keeps the guard the plan asked for
* Insights
    - A retargeted test whose name still describes the old assertion fails review even when the body is right
