---
task_id: warehouse-file-growth-m6
date: 2026-10-24
complexity_level: 3
---

# Reflection: warehouse-file-growth, milestone 6 (check pass)

## Summary

`stockroom.check` takes the writer flock and either records a rehearsal or, a day later, hard-links the original and replaces the live file with a new verified copy. The original stays at `warehouse.issue147-swap.duckdb`. QA passed. Nothing outside tests starts the pass.

## Requirements vs Outcome

The milestone's done text shipped, with two additions the first plan did not name.

Phase A writes `started`, calls `copy_warehouse`, writes `rehearsed` with the measurements, then deletes `warehouse.copy.duckdb`. A second call inside `86400` seconds does not copy again. Phase B copies again, hashes the original, `os.link`s it to the backup name, writes `linked`, fsyncs, and `os.replace`s the sibling onto `warehouse.duckdb`. When the backup hash matches, that same pass writes `swapped`. A failed link returns with the record still `started` and the warehouse bytes unchanged. Skips cover a missing home, a missing warehouse, a wal, `ST_RDONLY`, schema below the format boundary, low disk (`2 * live_bytes + 64 MiB`), and a busy flock. A stored skip walks that ladder again. Already-new is storage `v2.0.0+` and `large_column_zstd_problem` returning `None`. `entry` sets `signal.alarm` and installs no handler. `run_check` does not set the alarm. Doctor prints one `check` fact, `running` inside the limit and `overrun` past it. Troubleshooting gives four rename steps and says stockroom does not delete the backup. `SUBCOMMANDS`, hooks, `open`, and `open_current` are unchanged.

`linked` is the addition. The milestone text goes from the hard link to `swapped`. Preflight put a durable `linked` record between them so a crash after that write can finish without copying again. Finish-swap runs before leftover cleanup. Matching inodes and a sibling mean replace and write `swapped` from the stored measurements. Differing inodes mean write `swapped` and then delete a stray sibling. A missing sibling leaves the record `linked`.

The window before that record is durable stayed open. `os.link` can return, and the process can die, with the record still `started` and the backup name already taken. An expired `started` entry does not look at those inodes and does not replace. The operator accepted that on 2026-10-24. Deleting only `check.json` while `warehouse.issue147-swap.duckdb` is present makes the next `os.link` fail.

When the backup hash differs from the hash taken before the link, phase B returns without writing `swapped`. The replace has already happened. The next pass writes `swapped` because the inodes differ, and it does not hash again. The same-pass proof still holds on the path where the hashes match. The resume path follows the inode rule.

The session-start launch is milestone 7. This milestone leaves the pass dormant, which the milestone text requires.

## Plan Accuracy

The file list held: `check.py`, `storage.py`, `doctor.py`, `test_check.py`, `test_doctor.py`, `test_doctor_cli.py`, the troubleshooting page, and the probe index in preparation. No step was reordered in build. The plan was rewritten twice before that.

The first preflight failed because a schema-file warehouse is already new, so the alarm child would never sleep inside `copy_warehouse`, and because a stored skip had no `next_action` that builds again. The revision points the alarm child at `generations_file`, returns `phase-a` for a skip, treats a `v2.0.0+` file with a persistent non-zstd segment as not already new, and adds the `linked` resume.

The second preflight failed because leftover cleanup ran before finish-swap and would delete the sibling the resume has to rename. The revision finishes `linked` first. It also keeps an expired `started` entry final when the backup inode matches. A third preflight passed with advisories. The plan was not edited. Build followed that plan.

The challenges named before build were the ones that constrained the code: a Python handler does not interrupt DuckDB, `signal.alarm` must not be armed in the xdist worker, an unexpired start must keep its sibling, `live_bytes` is the disk estimate, and the link comes before the replace. Build did not meet a surprise outside that list. The hash-mismatch return is the inode resume rule applied one pass later, which the plan's finish-swap section already states.

## Creative Phase Review

The 4 hour ceiling held. `TIME_LIMIT_SECONDS` is `14400`. `entry` calls `signal.alarm` and does not install a handler. `run_check` does not. The child test passes `limit_seconds=1`. The ceiling was not timed against the 88 GB warehouse. The decision's tradeoff is unchanged: a stuck pass holds the writer flock until the alarm, and a false overrun needs a person to delete the record.

The free-disk comparison held. The pass skips when free disk is below `2 * live_bytes + 64 MiB`. Creative measured a 20 MB wal on an already-zstd fixture and rejected a 40× margin, because that file is already new and the pass will not copy it. Build did not reopen the margin. The accepted hole remains: a source the pass does copy, whose logical rows are much larger than its live bytes, can still fill the disk and leave a final `started` entry.

The doctor word held. Inside the limit the line is `running` and a later pass does not build. Past the limit the line is `overrun` and the entry is final. The word `crash` is not printed. The flock option stayed out, which mattered when preflight offered to finish a swap from directory entries: ingest holds the same flock, and an expired `started` entry stays final even when the backup inode matches.

None of the three decisions was a poor fit for the code. The state machine that preflight rewrote was not one of the open questions.

## Build & QA Observations

Build followed the eight steps. The engine suite recorded 1158 passed and 36 skipped, with `tests/test_coverage_collection.py` left out so `make coverage-engine` would not remove torch. Dashboard JavaScript recorded 134 passed. Ruff passed on the edited Python files. QA passed on the first run.

Two advisories, neither a build change. The module docstring still says later steps own the pass. The pass is `run_check` and `entry` in that module. No behavior reads the sentence. Phase B's hash mismatch leaves `linked`, and the next pass writes `swapped` from the inode split.

The implementation choice inside phase B is the early return at the backup hash. The tests required that return. QA judged it against the plan's resume rule and passed it.

## Cross-Phase Analysis

The first diagram sent a skip to quiet. The brief says a skip retries. Preflight caught that before a test could lock the wrong shape in. The same pass caught the alarm fixture: a schema-file warehouse never calls `copy_warehouse`, so a sleeping spy on that file would never run. Milestone 5's reflection had already said an empty column has no zstd segment and that milestone 6's already-new case has that shape. The non-zstd fixtures had to insert a real row and a `schema_version` row, or `current_version` is 0 and the pass records `below-boundary`.

The second diagram deleted the sibling and then tried to finish a `linked` swap. That sibling is the verified copy. Preflight caught a resume that would have thrown away the only file it can rename. The same round named the earlier window, where the backup exists and the record is still `started`. Coding a finish from those directory entries would replace a warehouse the overrun decision leaves alone. The operator kept the window open. QA did not reopen it.

The third preflight's advisories stayed out of the plan and did not come back as defects. One of them, a partial backup name until `linked` is durable, is the fix the operator declined. The hash-mismatch advisory is the inode rule on the following pass. Creative did not create either QA note. The docstring note is a stub sentence from the first implementation step that the later steps never replaced.

## Insights

### Technical

Finish a `linked` record before deleting `warehouse.copy.duckdb`. The sibling is the verified copy the resume renames into place.

A crash after `os.link` returns and before `linked` is durable stays `started`. An expired `started` entry does not replace the warehouse. The next `os.link` fails while `warehouse.issue147-swap.duckdb` exists, so clearing the record alone does not make phase B succeed. Milestone 7 must not finish that shape from directory entries.

A schema-file warehouse and an empty warehouse are already new. A test that must enter `copy_warehouse` uses `generations_file`, or a `v2.0.0+` file with a persistent non-zstd segment and a `schema_version` row. `signal.alarm` stays in `entry`. Finish-swap uses inodes. File size stays out of that decision.

### Process

Two fixable preflights, then a third that passed with advisories, then one build and one QA. The bugs were in the phase diagram. Splitting the rehearsal and the swap would have hidden the sibling-versus-resume bug until the second milestone.

A stub sentence that later steps own the pass is still in the module once those steps land there. QA will see it. It does not block.
