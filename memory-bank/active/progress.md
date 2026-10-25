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

## 2026-10-25 - PLAN - COMPLETE

* Work completed
    - Added a wait for a busy `swapped` value.
    - Named the check as the actor that replaces the live file while the record is `linked`.
    - Spoke of probe values, not of a line that starts with the status word.
    - Limited the day-later replacement to a warehouse that is still eligible.
    - Said `next_action` returns `phase-a`, and that readiness can still skip the copy.
* Decisions made
    - Do not say a `linked` value that stays `linked` means the live file is the original.
    - Say that a `swapped` record means the replacement has already happened.
    - Declined a read-only restore fact on the probe. The page keeps the branches.
* Insights
    - A failed write of `swapped` can leave the record `linked` after `os.replace`. The live file is then the new copy.

## 2026-10-25 - PREFLIGHT - COMPLETE

* Work completed
    - Validated the revised Level 2 plan against the hooks, `_readiness`, phase A and phase B, `_finish_swap`, `format_facts`, the doctor probe, and pull request 152 comment `4371593291`.
    - Wrote `FAIL (fixable)` as the first line of `.preflight-status`.
* Decisions made
    - The plan changes before build: the overrun recovery has to run when the backup is absent, the second probe has to re-enter the ladder, and the probe value is the field after the aligning spaces.
    - No `tasks.md` edit.
* Insights
    - An expired phase A `started` record has no swap backup. Later passes delete the sibling and leave `check.json`, so the check stays stopped.
    - `format_facts` pads after the colon. The text after `check:` does not start with the status word.

## 2026-10-25 - PLAN - COMPLETE

* Work completed
    - Split `overrun` with no backup file from the absent-backup stop.
    - Sent the probe after the one session back to the wait branch, with a 300-second or `busy` gate before a `linked` stop.
    - Defined the probe value as the text after the aligning spaces, and the comparison as its first word.
* Decisions made
    - Do not start a second session.
    - Do not move a backup file when the backup value is `absent`.
    - Declined a read-only restore fact again. The page keeps the branches.
* Insights
    - `format_facts` pads after the colon, so the characters immediately after `check:` are spaces.

## 2026-10-25 - PREFLIGHT - COMPLETE

* Work completed
    - Validated the revised Level 2 plan against the hooks, `_readiness`, phase A and phase B, `_finish_swap`, `format_facts`, the doctor probe, and pull request 152 comment `4371593291`.
    - Wrote `FAIL (fixable)` as the first line of `.preflight-status`.
* Decisions made
    - The plan changes before build: each new probe is read before the wait branch, and the linked stop's busy observation and 300-second clock start at the one session.
    - No `tasks.md` edit.
* Insights
    - Step 2 is the only instruction that reads the status word, and the re-probe steps skip it.
    - A `busy` warehouse value from before the one session is not evidence that session's check has run.

## 2026-10-25 - PLAN - COMPLETE

* Work completed
    - Required a read of the three first words after every new probe, before the wait branch.
    - Started the `linked` stop's `busy` observation and its 300-second clock at the one session.
    - Added one reply sentence: `doctor probe` still raises on the version-1 object.
* Decisions made
    - Forget a `busy` word from before the session.
    - Declined a read-only `restore` fact again.
* Insights
    - "Continue from step 3" skipped the only instruction that reads the probe.

## 2026-10-25 - PREFLIGHT - COMPLETE

* Work completed
    - Validated the revised Level 2 plan against the hooks, `_readiness`, phase B, `_finish_swap`, `format_facts`, the doctor probe, and pull request 152 comment `4371593291`.
    - Wrote `FAIL (fixable)` as the first line of `.preflight-status`.
* Decisions made
    - The plan changes before build: when the rename applies, which directory the file steps use, the 300-second linked stop, and the two halves of `already-new`.
    - No `tasks.md` edit.
* Insights
    - The backup file is present for `linked` and for `overrun`, so a present file is not the rename condition.
    - Both session-start hooks time out at 300 seconds, and the check launcher is the last command in that budget.
    - `already-new` requires storage `v2.0.0+` and no large-column zstd problem.

## 2026-10-25 - PLAN - STOPPED

* Work completed
    - Did not revise the plan for the fifth fixable preflight.
* Decisions made
    - Stopped after five preflight failures on the restore prose. The same class of gap has persisted past two revisions.
    - Build does not start until the operator chooses the shape of the restore page.
* Insights
    - The other four review calls are stable in the plan. The restore ladder is the part that does not stay true.

## 2026-10-25 - PLAN - COMPLETE

* Work completed
    - Claude Opus 5.5 took over the writing. Rewrote the brief and the plan so each prose unit carries the exact text to ship.
    - Wrote the restore page as situation, problem, solution, then nine steps, with a probe excerpt.
    - Wrote the GitHub reply text.
* Decisions made
    - Only `swapped` restores. `running` and `linked` complete first. Uncommon states stop and go to "Still stuck".
    - Forbid `warehouse.copy.duckdb` as the reader's name, because `_remove_sibling` deletes it.
    - Keep `check.json`, because a missing record starts phase A again.
* Insights
    - A plan that describes prose by rules invites a reviewer to find the next uncovered state. A plan that contains the prose can be checked claim by claim.

## 2026-10-25 - PREFLIGHT - COMPLETE

* Work completed
    - Sixth preflight: `FAIL (fixable)`. Steps 4 to 9 held. The status list and the problem paragraph claimed too much.

## 2026-10-25 - PLAN - COMPLETE

* Work completed
    - Named the six words that mean nothing to put back, and sent every other word to "Still stuck".
    - Scoped the problem paragraph to `running` and `linked`, and the `check.json` warning to after the restore.
    - Added the deleted-record caveat, the not-yet-migrated skip, and a `busy` wait after the one session.
    - Dropped the parenthetical definition of the new format.
* Decisions made
    - Narrow sentences, do not add branches.

## 2026-10-25 - PREFLIGHT - COMPLETE

* Work completed
    - Seventh preflight: `FAIL (fixable)`. Lifecycle, quickstart, deletion, and reply can ship. Steps 5 to 9 held.

## 2026-10-25 - PLAN - COMPLETE

* Work completed
    - Put the rename gate in step 4: `swapped` and a backup path, otherwise back to step 1.
    - Replaced the vague deleted-record caveat with a rule the reader can check: a backup path beside a word other than `swapped`, `running`, `linked`, or `overrun`.
    - Rewrote the solution as "wait until the check ends, then read the word."
* Decisions made
    - Kept `running` in the replace warning. A `running` phase B pass reaches `os.replace` in the same pass, so the finding that `running` is not a write was rejected.

## 2026-10-25 - PREFLIGHT - COMPLETE

* Work completed
    - Eighth preflight: `FAIL (fixable)`. Real step bugs: step 4 looped after a completed restore, and step 3 started the session while the warehouse was busy.

## 2026-10-25 - PLAN - COMPLETE

* Work completed
    - Replaced the status list with one gate: rename only on `swapped`, wait on `running` or `busy`, one session on `linked`, stop on any other word.
    - Step 1 now ends on `backup: absent`, which also ends the procedure after the restore.
    - Qualified the day-later replacement, the restart after a skip, and a failed verification.
* Decisions made
    - Gave up telling readers of other status words that there is nothing to put back. Every per-state claim drew a new edge case.

## 2026-10-25 - PREFLIGHT - COMPLETE

* Work completed
    - Operator stopped the ninth preflight and consulted Gemini Argon 4, GPT-5.6 Sol, and Muse Wonder.
    - All three: the gate is safe, the per-state truth test is unbounded, do not run another preflight.
    - Applied two edits: the opening says the original stays in place if a step fails, and step 8 uses the fixed name `warehouse.replaced.duckdb`.
    - Recorded `PASS WITH ADVISORY` by operator decision. The restore page is judged on harm only.
* Insights
    - A preflight that checks prose against every state of a state machine does not converge. Judge a human procedure on whether it can cause harm.

## 2026-10-25 - PREFLIGHT - COMPLETE

* Work completed
    - Validated the Level 2 prose plan against the hooks, `_readiness`, phase A and phase B, `_finish_swap`, `format_facts`, the doctor probe, and pull request 152 comment `4371593291`.
    - Wrote `FAIL (fixable)` as the first line of `.preflight-status`.
* Decisions made
    - The plan changes before build: the copy-condition sentences, and the problem and solution sentences that are not true for every probe word.
    - Steps 4 through 9 stay. No `tasks.md` edit.
* Insights
    - Schema below 9 is `skip` / `below-boundary`, and `already-new` compares the storage tag `v2.0.0+`.
    - An expired `started` record and a stuck `linked` record never become `swapped`. Deleting `check.json` while the backup name remains does not make `os.link` succeed.

## 2026-10-25 - PREFLIGHT - COMPLETE

* Work completed
    - Validated the revised Level 2 prose plan against the hooks, `_readiness`, `copy_warehouse`, phase A and phase B, `_finish_swap`, `format_facts`, the doctor probe, and pull request 152 comment `4371593291`.
    - Wrote `FAIL (fixable)` as the first line of `.preflight-status`.
* Decisions made
    - The plan changes before build: the `running` write sentence, the promise that the word becomes `swapped`, the `absent` claim, and a gate before step 4.
    - Steps 5 to 9 stay. No `tasks.md` edit.
* Insights
    - The live file is replaced only after `linked` is written. A `running` word is still a `started` record, and `copy_warehouse` does not open the original for writing.
    - `absent` is a missing `check.json`. After a landed swap that word can sit on the new copy while the backup line is still a path.

## 2026-10-25 - PREFLIGHT - COMPLETE

* Work completed
    - Validated the revised Level 2 prose plan against the hooks, `_readiness`, phase A and phase B, `_finish_swap`, `format_facts`, the doctor probe, and pull request 152 comment `4371593291`.
    - Wrote `FAIL (fixable)` as the first line of `.preflight-status`.
* Decisions made
    - The plan changes before build: the copy overview, the `running` and `absent` claims, the solution paragraph, and steps 3 and 4.
    - Lifecycle, quickstart, the schema-head deletion, the dismiss reply, and steps 5 to 9 stay.
    - No `tasks.md` edit.
* Insights
    - `os.replace` of the live file runs only after `linked` is written.
    - A `skip` on the phase B day overwrites the `rehearsed` record, and the next pass is phase A.
    - A `linked` session that loses the flock does not finish the swap, and `swapped` with an absent backup loops if step 4 returns to step 1.
