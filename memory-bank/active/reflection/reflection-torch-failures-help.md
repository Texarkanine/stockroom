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

# Reflection: torch-failures-help (rework)

## Summary

When torch cannot be imported and a usable hashed freeze exists, `stockroom semantic` and `stockroom embed` restore it once and retry. The other two failures name `sr-initialize` and do not claim a command that cannot be run. The build succeeded. QA passed with advisories and no code change.

## Requirements vs Outcome

The rework in the project brief is what shipped. A usable freeze runs `ensure_engine_env` once, prints `restoring torch from the hashed freeze`, and retries. A failed restore names its reason and `sr-initialize`. No freeze, and any other encoder exception, name `sr-initialize` without a pip template or a wrong-wheel claim. `doctor smoke` still only reports, and its usable-freeze line still names `stockroom shim ensure-env`. The first reflection's three-way "print a command" outcome is withdrawn.

## Plan Accuracy

The file list held. Two preflight advisories were adopted: retry unless the report is `failed` (so `noop` retries), and `importlib.invalidate_caches()` before that retry. The generic wrapper advisory was left rejected. The plan's red-then-green sequence was not captured as two pytest runs.

## Build & QA Observations

`make ci` passed: 1018 tests, 38 skipped, ruff clean, reuse compliant. QA found no defect. It left three advisories: one clause in `system-model.md` says the embed connection stays read-only, which is the wrong description of embed's later open; the new test helpers are duplicated the way this suite already duplicates helpers; the retry-still-fails test exists only on semantic, which is the shared function. None of those asked for another build.

## Insights

### Technical

- Naming `stockroom shim ensure-env` was the right diagnosis and the wrong delivery. The freeze already chooses the wheel, so the command can run that restore itself. The no-freeze line and the encoder-exception line were guesses, and printing them as if they were repairs taught the agent a command it could not run.

### Process

- The first pytest run of the new tests was already green, so the red step is a note in `activeContext.md` rather than a captured failure. QA still treated the assertions as real pins.

## Million-Dollar Question

This is the shape the first design was reaching for. Session start already heals from the freeze. Semantic and embed are the backup when that heal did not leave torch importable, and doctor smoke stays the check that can still show a missing torch. The pip template and the "pick a different wheel" sentence would not have been printed.
