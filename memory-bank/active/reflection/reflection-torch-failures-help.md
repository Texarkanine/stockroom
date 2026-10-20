---
task_id: torch-failures-help
date: 2026-10-20
complexity_level: 2
---

# Reflection: torch-failures-help

## Summary

`stockroom semantic` and `stockroom embed` now exit 1 with one stderr line when the encoder cannot be constructed, and the skill names that same line. The build succeeded. QA passed with one non-blocking test gap.

## Requirements vs Outcome

Issue #144 is resolved. The ticket's two-way split (freeze present means `stockroom shim ensure-env`, otherwise `sr-initialize`) was not implemented. A usable freeze plus an encoder exception is a bad wheel, and ensure-env would reinstall it. The commands use the three-way split `doctor smoke` already had. The skill, the torch contract, and the torch page say the same thing. `docs/user-guide/load/basic.md` was updated because it quoted the old heading. The non-draft pull request is the remaining delivery step.

## Plan Accuracy

The plan's file list and order held. The challenges that mattered were the ones named up front: catch only `encoder_factory()`, let a non-torch `ModuleNotFoundError` propagate, and keep the remedy strings in one place. No step had to be redone.

## Build & QA Observations

The new CLI tests failed on the uncaught exception, then passed once the catch printed the shared line. Existing doctor smoke tests stayed green after they started calling those functions. QA re-ran the three test modules and found no defect. It noted that no test raises `ModuleNotFoundError` named `torch.<submodule>`. That branch is real and unpinned. It is not an acceptance gap.

## Insights

### Technical

- Whether a freeze exists is the wrong key for every encoder failure. ensure-env replays the freeze, so it is the remedy only when torch itself cannot be imported. A failure after that import needs a different wheel.

### Process

- The agent followed the skill row that matched the traceback, not the troubleshooting page. A remedy that lives only in the docs does not reach that agent. The stderr line and the skill row both had to change.

## Million-Dollar Question

The shape we built is the one this would have had from the start: the remedy clauses live next to the encoder, and every caller that prints a torch failure uses them. Putting the catch inside `BgeEncoder` would have mixed a library exception with CLI policy.
