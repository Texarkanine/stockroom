# Project Brief

## User Story

As a person who keeps a stockroom warehouse, I want the warehouse-check text to match what the check does, so I do not follow a false sentence or a restore that can meet a running check.

## Use-Case(s)

### Use-Case 1

A reader of the lifecycle page learns that session start runs rectify and the dashboard, then starts the check and does not wait for that child.

### Use-Case 2

A reader of the quickstart and the troubleshooting page learns that rehearsal and replacement apply to an eligible existing warehouse. A new-format warehouse is recorded `already-new` and is left in place.

### Use-Case 3

A reader who wants the original warehouse back can tell that the situation applies, what the problem is, and what the restore is, before any rename. The reader renames only when the check value starts with `swapped` and the warehouse value is not `busy`. A `running` value, a busy `linked` value, or a busy `swapped` value means wait. A `linked` value that is not busy means start one session and probe again. A value that stays `linked`, or a value that starts with `overrun`, means stop. Do not claim that a value which stays `linked` means the live file is still the original. `overrun` uses the other recovery: move the backup aside, then delete `check.json`.

### Use-Case 4

`stockroom doctor probe` does not claim to report schema lag, and it does not call the unused schema-head comparison.

## Requirements

1. In `docs/architecture/lifecycle.md`, replace "The hook command itself returns at once" with a true sentence. The hook runs rectify and the dashboard, then starts the check and does not wait for that child.
2. In `docs/user-guide/quickstart.md` and `docs/user-guide/troubleshooting/index.md`, say that rehearsal and replacement apply to an eligible existing warehouse, and that a new-format warehouse is recorded `already-new` and is not rehearsed or replaced.
3. Rewrite the troubleshooting warehouse section in the spirit of ASD-STE100. Before the numbered steps, say three things: how to know the situation applies, what the problem is, and what the solution is. Then give the steps. Rename only when the check value starts with `swapped` and the warehouse value is not `busy`. Keep the writer-stop instruction and the instruction to read the backup path. A `running` value, a busy `linked` value, or a busy `swapped` value means wait and probe again. A `linked` value that is not busy means start one session and probe again; rename only if the new value starts with `swapped`, and stop if it is still `linked`. An `overrun` value means move `warehouse.issue147-swap.duckdb` aside and delete `check.json`, and do not use the rename steps. Say that while the record is `linked`, the check can put the new copy on `warehouse.duckdb`. Do not change the check state machine.
4. Reply on GitHub review comment `discussion_r4371593291` and dismiss the malformed-`started` finding. Limit the reply to a version-1 `started` object: `KeyError` or `TypeError` in `check_line` and `next_action`, and the child dies before phase A. State that any other `check_version` makes `next_action` return `phase-a`, and that readiness can still skip the copy. Do not change `check_line`.
5. Delete the no-op `current_version(con) < _latest_version(): pass` block in `storage_facts` and the imports that exist only for it. Do not add a schema-behind fact.
6. Leave `os.fsync` as it is. Do not add `F_FULLFSYNC`. Do not reply on that nit.

## Constraints

1. Do not change the "click here!" link text in the quickstart.
2. Do not change `check.py` state selection, `_finish_swap`, or `_fsync`.
3. Do not add a doctor fact for schema lag.
4. Troubleshooting prose follows ASD-STE100: short sentences, one meaning per word, active voice. Keep the precise names `warehouse.duckdb`, `warehouse.issue147-swap.duckdb`, `swapped`, `already-new`, and `stockroom doctor probe`.
5. This work is on branch `warehouse-file-growth` for pull request 152.

## Acceptance Criteria

1. `docs/architecture/lifecycle.md` does not say that the hook command returns at once. It says the hook runs rectify and the dashboard, then starts the check and does not wait for that child.
2. The quickstart and the troubleshooting page both say that rehearsal and replacement apply to an eligible existing warehouse, and that a new-format warehouse is recorded `already-new` and is not rehearsed or replaced. The replacement is at least one day after the rehearsal, and only if the warehouse is still eligible. The quickstart link text is still "click here!".
3. The troubleshooting warehouse section states when the restore applies, what the problem is, and what the restore is, and only then lists the steps. The steps rename only when the check value starts with `swapped` and the warehouse value is not `busy`. They include the writer stop, the backup path, and the two renames. They also say what to do for `running`, `linked`, busy `swapped`, and `overrun`. The problem names the check, not the reader, as the actor that can put the new copy on `warehouse.duckdb` while the record is `linked`.
4. Comment `4371593291` has one dismiss reply from the operator's `gh` account. `check_line` is unchanged.
5. `storage_facts` has no schema-head comparison and no import used only by that comparison. `test_storage_below_head_does_not_change_the_file` still passes. Probe facts do not grow a schema-lag line.
6. `check.py` and `storage.py` still call `os.fsync` only. No review reply is posted for the full-flush nit.
