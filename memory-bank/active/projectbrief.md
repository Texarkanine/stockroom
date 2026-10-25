# Project Brief

## User Story

As a person who keeps a stockroom warehouse, I want the warehouse-check text to match what the check does, so I do not follow a false sentence or a restore that can meet a running check.

## Use-Case(s)

### Use-Case 1

A reader of the lifecycle page learns that session start runs rectify and the dashboard, then starts the check and does not wait for that child.

### Use-Case 2

A reader of the quickstart and the troubleshooting page learns that the check moves an older warehouse to the new format only when it is safe, in two steps a day apart, and leaves a warehouse that is already new as it is.

### Use-Case 3

A reader who wants the original warehouse back first learns when this applies, what the problem is, and what the solution is. The reader renames only on a `swapped` record. `running` and a busy warehouse wait. `linked` gets one new session. Every other status stops at "Still stuck". Then the reader follows short steps.

### Use-Case 4

`stockroom doctor probe` does not claim to report schema lag, and it does not call the unused schema-head comparison.

## Requirements

1. In `docs/architecture/lifecycle.md`, replace "The hook command itself returns at once" with a true sentence about what the hook waits for.
2. In `docs/user-guide/quickstart.md`, qualify the warehouse-check sentence: only when safe, two steps, at least a day apart, and an already-new warehouse is left as it is.
3. Rewrite the troubleshooting `## Warehouse` section in the spirit of ASD-STE100. Before any procedure, state when the restore applies, what the problem is, and what the solution is. Then give the steps. The text to ship is in `tasks.md`.
4. Reply on GitHub review comment `discussion_r4371593291` and dismiss the malformed-`started` finding. The text to post is in `tasks.md`. Do not change `check_line`.
5. Delete the no-op `current_version(con) < _latest_version(): pass` block in `storage_facts` and the imports that exist only for it. Do not add a schema-behind fact.
6. Leave `os.fsync` as it is. Do not add `F_FULLFSYNC`. Do not reply on that nit.

## Constraints

1. Do not change the "click here!" link text in the quickstart.
2. Do not change `check.py` state selection, `_finish_swap`, or `_fsync`.
3. Do not add a doctor fact or a command for the restore.
4. The troubleshooting page is a human procedure, not a decision table for every record state. Uncommon states stop and go to "Still stuck".
5. This work is on branch `warehouse-file-growth` for pull request 152.

## Acceptance Criteria

1. `docs/architecture/lifecycle.md` does not say that the hook command returns at once.
2. The quickstart sentence says the move happens only when safe, in two steps at least a day apart, and that an already-new warehouse is left as it is. The quickstart link text is still "click here!".
3. The troubleshooting warehouse section states when the restore applies, the problem, and the solution, and only then lists the steps. Each claim matches `check.py`: renames happen only from `swapped`, writers are stopped, the replaced file is not named `warehouse.copy.duckdb`, a `.wal` moves with its file, and `check.json` is kept.
4. Comment `4371593291` has one dismiss reply from the operator's `gh` account. `check_line` is unchanged.
5. `storage_facts` has no schema-head comparison and no import used only by that comparison. `test_storage_below_head_does_not_change_the_file` still passes.
6. `check.py` and `storage.py` still call `os.fsync` only. No review reply is posted for the full-flush nit.
