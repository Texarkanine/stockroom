---
task_id: warehouse-check-review-wording
date: 2026-10-25
complexity_level: 2
---

# Reflection: Warehouse-check review wording

## Summary

The pull request 152 follow-up shipped: three doc corrections, the deletion of a dead schema-head comparison, and one dismiss reply on GitHub. QA passed on the first build. The plan took eight fixable preflights and a three-model consult before build.

## Requirements vs Outcome

All six requirements were met. Two were reshaped during planning. The quickstart sentence gained a link to the troubleshooting section. The restore page changed from a per-status guide to one rename gate, so readers whose check word is not `swapped`, `running`, or `linked` now stop at "Still stuck" and are not told which file is the original.

## Plan Accuracy

The code and GitHub units held from the first plan. The restore page did not. The first five plans described it by rules, and each preflight found a check state the rules missed. Writing the page text into the plan made the claims checkable, but a status list kept drawing new edge cases. The challenge list named this risk, as a decision table that would grow, but the plan did not act on it until the operator stopped the loop.

## Build & QA Observations

The build was mechanical. A script copied the doc text from `tasks.md` into the pages, and QA compared the bytes by script. QA found nothing that had to change. It flagged two older doc inaccuracies outside this change: the `storage_facts` docstring says the backup line appears "only when" the file exists, and the lifecycle bullet says stdout and stderr are discarded, but the Cursor hook discards only stdout. Separately, the progress log had entries out of order, because plan entries were inserted after an anchor while preflight subagents appended at the end. It was fixed before reflect.

## Insights

### Technical

- `_remove_sibling` deletes `warehouse.copy.duckdb` on every non-running, non-resuming pass, including after `swapped`. That file name is not safe for a person to use beside the warehouse.

### Process

- Do not have a preflight check a human recovery procedure against every state of a state machine. That check has no end. Judge the procedure on harm: does it ever tell the reader to act when the gate is not met? Settle that test in the plan before the first preflight.
- When the plan's subject is prose, put the exact text in the plan from the start. A plan that describes prose by rules gives the reviewer an unbounded target.
- Append progress entries at the end of the file. Inserting after an anchor breaks time order once subagents also write to the log.

### Million-Dollar Question

If the restore had been part of the swap design from the start, a person would not run it by hand. A small command would hold the writer flock, rename only when the record is `swapped`, and refuse otherwise. The troubleshooting page would then say one thing: run that command. The operator ruled out a new command for this task, so the page carries the gate in prose instead.
