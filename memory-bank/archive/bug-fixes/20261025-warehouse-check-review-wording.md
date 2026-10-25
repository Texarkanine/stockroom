---
task_id: warehouse-check-review-wording
complexity_level: 2
date: 2026-10-25
status: completed
---

# TASK ARCHIVE: Warehouse-check review wording

## SUMMARY

Corrected the warehouse-check text on pull request 152. The lifecycle page no longer says the hook returns at once. The quickstart says the check moves an older warehouse only when it is safe, in two steps at least a day apart, and leaves a new-format warehouse as it is. The troubleshooting restore renames files only when `stockroom doctor probe` shows `swapped`, a warehouse path, and a backup path. A dead schema-head comparison in `storage_facts` was deleted. The malformed-`started` review comment was dismissed. QA passed on the first build.

## REQUIREMENTS

1. Replace the false hook sentence with what the hook actually waits for.
2. Qualify the quickstart check sentence, and leave the "click here!" link text as it is.
3. Rewrite the troubleshooting warehouse section so the reader learns when it applies, what the problem is, and what the solution is, before any step.
4. Dismiss the malformed-`started` comment. Do not change `check_line`.
5. Delete the no-op schema-head comparison. Do not add a schema-lag fact.
6. Leave `os.fsync` and the check state machine as they are.

Two requirements changed shape during planning. The quickstart sentence gained a link to the troubleshooting section. The restore page became one gate instead of a guide for every check word, so a reader whose word is not `swapped`, `running`, or `linked` stops at "Still stuck" and is not told which file is the original.

## IMPLEMENTATION

- `docs/architecture/lifecycle.md`: the hook waits for rectify and the dashboard, then starts the check as a detached child and returns without waiting for it.
- `docs/user-guide/quickstart.md`: the qualified check sentence, with the "click here!" token unchanged.
- `docs/user-guide/troubleshooting/index.md`: the `## Warehouse` section. Rename only on `swapped`. Wait on `running` or `busy`. Start one session on `linked`. Stop on any other word. The replaced file is renamed to `warehouse.replaced.duckdb`, never `warehouse.copy.duckdb`, and a `.wal` moves with its file. `check.json` stays.
- `skills/sr-search/src/stockroom/doctor.py`: removed the `pass` comparison and the `current_version` and `_latest_version` imports.
- GitHub reply on comment `4371593291`: `discussion_r4372377536`. Disposition: dismiss. No code change.

## TESTING

The below-head doctor test passed before and after the deletion. The full local run was ruff, format, REUSE, schema-docs, migrations, a strict docs build, 134 dashboard JavaScript tests, and pytest: 1164 passed, 36 skipped. `test_coverage_collection.py` was left out of the local run because it removes torch. QA passed on the first review and compared the shipped doc bytes to the plan text.

## LESSONS LEARNED

- `_remove_sibling` deletes `warehouse.copy.duckdb` on every pass that is not running and not resuming a swap, including after `swapped`. A person must not use that name beside the warehouse.
- Do not check a human recovery procedure against every state of a state machine. That check has no end. Judge it on harm: does the page ever tell the reader to rename before the gate is met, delete `check.json`, or use `warehouse.copy.duckdb`?
- When the plan's subject is prose, put the exact text in the plan from the start.
- Append progress entries at the end of the file. Inserting after an anchor breaks time order once another writer appends.

## PROCESS IMPROVEMENTS

Settle the harm test in the plan before the first preflight of a procedure. Eight fixable preflights and a three-model consult were the cost of not doing that. The operator then recorded `PASS WITH ADVISORY` and the build proceeded.

## TECHNICAL IMPROVEMENTS

If the restore had been part of the swap from the start, a small command would hold the writer flock, rename only when the record is `swapped`, and refuse otherwise. The page would say: run that command. The operator ruled out a new command for this task, so the page carries the gate in prose.

## NEXT STEPS

Two older doc inaccuracies were seen and left alone. The `storage_facts` docstring says the backup line appears only when the file exists, but the probe always prints a `backup` line. The lifecycle doctrine says stdout and stderr are discarded, but the Cursor hook discards only stdout.
