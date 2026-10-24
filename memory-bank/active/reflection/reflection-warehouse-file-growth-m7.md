---
task_id: warehouse-file-growth-m7
date: 2026-10-24
complexity_level: 2
---

# Reflection: warehouse-file-growth, milestone 7 (session-start launch)

## Summary

Session start now starts the check and returns at once. The child is detached the way the dashboard is, and `beforeSubmitPrompt` does not start the check. QA passed on the first review.

## Requirements vs Outcome

The milestone's done list is in place: both session-start hooks, the detached launch, a test that a final record does not build, hook coverage for both harness files, the user-facing description, and an empty install that records `already-new` and builds nothing. `stockroom check` was not added. `entry` and `run_check` were not changed. The DuckDB import on the hook parent stayed an advisory, as the plan said.

## Plan Accuracy

The sequence held. The first preflight failed on two fixable gaps: a launched child cannot import `stockroom` unless the test sets `PYTHONPATH`, and two user-guide sentences still said session start only heals the shim and launches the dashboard. The second preflight passed with advisories, and the plan was not edited for those. Two tests were already green before production code existed: `stockroom check` was already unknown, and the empty install already recorded `already-new` once `launch` existed.

## Build & QA Observations

The launch tests went red on `NotImplementedError` and then passed. The hook tests went red on the missing command token and then passed. QA found no behavior gap. The advisories are the DuckDB import, a lifecycle sentence that still calls a repeated session start a no-op, and two sentences that still say every caller goes through the shim.

## Insights

### Technical

- pytest's `pythonpath` does not reach a child, and `DEVNULL` hides the import error. A detached-process test has to set `PYTHONPATH` itself.
- A hook-command assertion that runs from the word `dashboard` to the end of the string will reject the next command. Stop that slice at the next `;`.

### Process

- A lock test for a command that must stay absent is green before the work starts. Forcing it red would invent a failure.

### Million-Dollar Question

The launch we built is the small version of the right shape: one detached child in front of `entry`, invoked as a module so it never appears in `stockroom --help`. A separate standard-library launcher would make the hook parent skip the DuckDB import. The pass would still be the same child.
