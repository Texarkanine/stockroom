---
task_id: warehouse-file-growth
date: 2026-10-22
complexity_level: 3
---

# Reflection: Move the engine to DuckDB 2.0 (warehouse-file-growth, milestone 2)

## Summary

The engine now runs DuckDB 2.0.0 (`ac8c6ca`, `feat!:`). Before the lock landed, the full suite passed on a 2.0 overlay with torch, and the shadow script passed on a copy of this machine's warehouse. The nanobind exit warnings were fixed at their cause, stockroom's own Hub-notice logger filter. This machine's live warehouse then took its first 2.0 writes under supervision, and DuckDB 1.5.4 can still open it. QA passed with five advisories, none blocking.

## Requirements vs Outcome

Every item on milestone 2's done list was delivered:
- **Engine:** the range is `>=2.0,<2.1` and the lock pins 2.0.0. Dependabot ignores duckdb `>=2.1.0` in the engine block.
- **Shadow script:** the new checks are a copy at the schema head with no index and the old tag, a ranked `semantic` hit, and no `nanobind` line from any stockroom command. The script exited 0 on a copy of this machine's warehouse, run from a fresh clone.
- **Docs:** the doc page says which DuckDB opens the warehouse.
- **Nanobind:** `embed` and `semantic` print no nanobind lines under 2.0.
- **Landing:** the 2.0 move is one commit and landed last.

Nothing was descoped. Two items were added:
- an `-rs` run to prove the torch-gated tests ran in gate 4a;
- after QA, a full run of the docstring's 2.0-lock form from a fresh clone of the landed branch. QA had flagged that form as never run end to end. Result: it passed. It ran from a clone of `622556c` with `make sync` and no `--with`, and torch went into the clone's own `.venv` from the hashed freeze. It exited 0 with `shadow: every phase passed` on a copy of the live warehouse after the live 2.0 writes, with no `nanobind` line. DuckDB 1.5.4 still wrote that copy.

Still open: the release gate. The operator runs the shadow script from a fresh clone on his Macs, and the pull request title must start `feat!:`.

## Plan Accuracy

The plan's order and file list held exactly, and no step needed reordering or splitting. The planning measurements held: the nanobind cause, the lock resolving with only duckdb changing, the new-file tag, and the suite on a 2.0 overlay. Three surprises came from places the plan did not look:

- **Test-process noise.** On DuckDB 2.0.0, a pytest process that loads the engine `conftest` and imports torch in-process prints nanobind leak lines at exit. Its exit code is unchanged. Planning had established, correctly, that a torch-free process does not reproduce the warning. It had not looked at the test runner itself. The noise first showed after N5's red run, and probes narrowed it to torch in the pytest process. Stockroom's command processes are clean.
- **Lock file format.** uv 0.12.22 rewrote the engine lock from `revision = 3` to `5` and dropped scipy's numpy markers. The planning-time scratch relock said "only duckdb changes", which was true of the package set but not of the file. A comparison by name, version, and source confirmed it at step 5.2.
- **Skip counts.** Gate 4a's expectation, "fewer skips than 38", could not prove that the torch-gated tests ran. Two tests skip the other way round: one when torch is installed, one when torch is already loaded in the worker. The count moved by 3 for 5 gated tests, and only an `-rs` run settled it.

The challenges the plan named did happen and were handled as written:
- **Torch stripped by commits.** The commit hook's exact sync removed torch from the live `.venv` at the landing commit, the final `make ci`, and each later phase commit. `stockroom shim ensure-env` put it back each time.
- **Dashboard.** The bounce worked.
- **Rollback copy.** The backup stayed byte-identical to the live file until the first live 2.0 write, which came after both gates.

## Creative Phase Review

No creative phase ran. The one open design question was how to remove the nanobind warnings. It was settled by measurement in planning: a context manager around the model load. That held in build without friction. The torch-free tests (N3 and N4, with fake modules) and the torch-gated end-to-end test (N5, red then green on the overlay) each checked a different layer of it.

## Build & QA Observations

- **TDD:** red and green were clean for both executable units, and every gate passed on its first run.
- **Overlay script:** writing the 2.0 overlay invocation once, as a commented scratch script (`m2/overlay20.sh`), turned N5's red and green runs, gate 4a, and the `-rs` check into one-line runs. It also avoided the path slip that preflight found.
- **Interface stub:** turning the function into a context manager meant that a bare call in `BgeEncoder` would silently add nothing. So the `with` went in with the interface stub, while the stub's body still added the filter for good. Behaviour did not change until the green step.
- **QA findings:**
  - A stale `test_embed.py` module docstring, my miss. I fixed it in `622556c`.
  - "Overlay" naming in the shadow script for the 2.0-lock form. Cosmetic; left as it is.
  - The 2.0-lock run form never run end to end. Closed by the extra run above, which passed.
  - The pytest-plus-torch noise, recorded only in context. See Insights.
  - Torch stripped again by the QA-save commit. Operational; `ensure-env` restores it.

## Cross-Phase Analysis

- **Preflight paid off directly.**
  - Advisory 1 (the `uv --directory` form) prevented a loud but wasteful failure in the N5 red run and gate 4a.
  - Advisory 4 put `doctor smoke`, a third `BgeEncoder` path, into the live checks, and it passed.
  - Advisory 5 (gate 4b from a fresh clone) proved the clone recipe on this machine. It proved only the 1.5.4-lock form, though, because the clone predated the lock. Once the lock landed, the recipe's main form became the untested one. QA caught that gap, and one more run, which passed, closed it.
- **Planning's narrower probe left the noise unexplained.** Planning checked "does a torch-free process reproduce the warning?" and not "does the test runner print it?". So the build met the noise unexplained and spent three probes on it. Those probes were cheap, and they kept a test-process effect from being mistaken for an unfixed product leak.

## Insights

### Technical
- **Logger filters on third-party loggers:** a filter instance left on such a logger for the life of the process keeps its defining module's globals alive, through the class's methods, until interpreter shutdown. With a nanobind-based extension such as DuckDB 2.0, that shows up as leaked-instance warnings at exit. Scope such filters to the call that needs them.
- **Judging an exit-time leak fix:** check the command processes themselves, not the test runner's exit output. A pytest process that imports torch next to the engine `conftest` prints the same nanobind lines without any product leak.
- **Skip counts do not show that gated tests ran:** this suite has tests that skip the other way round (torch installed, torch already loaded), so use `-rs`.
- **Confirming "only X changed" in a relock:** compare the package sets by name, version, and source, not the raw diff. uv 0.12.22 rewrites an older lock's format on any relock.

### Process
- **Recipes with several run forms:** when the landing changes which form applies, run the post-landing form once after landing, from a fresh clone of the landed commit. Proving the pre-landing form proves only that one.
