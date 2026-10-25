# Progress

Correct the warehouse-check sentences on pull request 152, rewrite the troubleshooting restore so the reader knows when it applies before the steps, delete the dead schema-head comparison, and dismiss the malformed-record comment. Leave the check state machine and `os.fsync` as they are.

**Complexity:** Level 2

## 2026-10-25 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - Confirmed no ephemeral state was in flight, then restated the six review calls.
    - Operator approved the restatement and added the troubleshooting order: situation, problem, solution, then steps, in ASD-STE100.
    - Classified the work as Level 2.
* Decisions made
    - Fix the false hook sentence, the already-new qualification, and the restore steps.
    - Delete the no-op schema-head comparison. Do not report schema lag.
    - Dismiss the malformed `started` finding with a pull-request reply and no code change.
    - Do not add `F_FULLFSYNC` and do not reply on that nit.
    - Do not change the quickstart "click here!" link text.
* Insights
    - `test_storage_below_head_does_not_change_the_file` already locks the observable probe contract for a warehouse below the schema head.

## 2026-10-25 - PLAN - COMPLETE

* Work completed
    - Planned three documentation edits, the deletion of the dead schema-head comparison, and one dismiss reply on comment `4371593291`.
    - Mapped the deletion to the existing doctor test. Added no new test.
* Decisions made
    - Troubleshooting order is situation, problem, solution, then steps, in ASD-STE100.
    - The quickstart "click here!" token stays byte for byte.
    - No schema-lag fact. No `F_FULLFSYNC`. No check-state change.
* Insights
    - A red test for this deletion would not go red for a missing outcome. The `pass` body has none.

## 2026-10-25 - PREFLIGHT - COMPLETE

* Work completed
    - Validated the Level 2 plan against the hook commands, `check.py`, the doctor probe, and pull request 152 comment `4371593291`.
    - Wrote `FAIL (fixable)` as the first line of `.preflight-status`.
* Decisions made
    - The plan changes before build: the restore wait, the rehearsal sentence, and the dismiss reply.
    - No `tasks.md` edit. Unit 4 stays on the existing below-head test, with no new test.
* Insights
    - A stopped `linked` record reaches `swapped` only on a later check pass, and some `linked` and `started` records never do.
    - `_readiness` skips several warehouses that are not `already-new`.
    - `next_action` reads `started_at` only for check version 1.

## 2026-10-25 - PLAN - COMPLETE

* Work completed
    - Revised the troubleshooting branches, the eligible-warehouse sentence, and the dismiss reply after the fixable preflight.
    - Took the day-wait advisory so "a later session start" is not read as the next session.
    - Declined a new flock-owning restore command.
* Decisions made
    - Rename only when the check line starts with `swapped` and the warehouse is not busy.
    - Eligible keeps the `_readiness` skips, including schema version 9 and the free-disk floor.
    - The GitHub reply names `KeyError` and `TypeError` for check version 1 only.
* Insights
    - Waiting for `swapped` without a new session deadlocks a child that already exited at `linked`.

## 2026-10-25 - PREFLIGHT - COMPLETE

* Work completed
    - Validated the revised Level 2 plan against the hooks, `_readiness`, phase A and phase B, `_finish_swap`, the doctor probe, and pull request 152 comment `4371593291`.
    - Wrote `FAIL (fixable)` as the first line of `.preflight-status`.
* Decisions made
    - The plan changes before build: a `swapped` line while the warehouse is busy, and the linked-window rename sentence.
    - No `tasks.md` edit.
* Insights
    - The check writes `swapped` before it leaves the writer flock, so probe can show `swapped` and `warehouse: busy` together.
    - The check's `os.replace` puts the new copy on `warehouse.duckdb` while the record is still `linked`. A reader rename in that window does not.
