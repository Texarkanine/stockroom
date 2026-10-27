---
task_id: fortnight-backup-and-quiet-check
date: 2026-10-27
complexity_level: 3
---

# Reflection: Fortnight backup reclaim and finished-home short-circuit

## Summary

The swapped stop path unlinks `warehouse.issue147-swap.duckdb` 14 days after `started_at` when the inodes differ, and the session-start parent returns without a child and without DuckDB when that child would leave the disk alone. The build matches the revised plan. QA passed.

## Requirements vs Outcome

Every requirement in the brief is in the code. The backup goes only on the version-1 `swapped` stop path, under the writer flock, and `check.json` is not rewritten. The parent launches for an unfinished home and for a due backup, and returns for a young swap, a same-inode name, a missing clock, a missing live warehouse, and for `already-new` or `mismatch` even when a backup file is present. The hook files are unchanged. Item 2 of issue 155 stayed out.

Additions beyond the first draft of the plan, all from the operator revision or the second preflight:

- One `_swap_backup_due` for the gate and the unlink. `OSError` from that call starts the child and does not unlink.
- One sentence in `docs/architecture/lifecycle.md`.
- The existing expired-start test carries the fortnight, instead of a second test.
- Extra tests for a bool `started_at`, a stat error, and `--foreground` on a young swap.

The user guide says "14 days." That is the same interval as a fortnight, in the same voice as "one day" in that section.

## Plan Accuracy

The revised plan's order held: unlink, then the quiet parent, then the guide. The file list was right. `lifecycle.md` was the one file the plan did not name; the preflight advisory added one sentence there.

The challenges in the plan were the ones that showed up. `bool` is an `int`. A clock-only gate would launch forever when the inodes match. Importing `duckdb` alone would not quiet the parent, because `storage` and `warehouse` import it. The foreground branch had to stay first.

The first plan, before the operator revision, would have launched whenever the backup file existed. That plan was preflighted and then retired. The surprises that were not in the plan were environmental: the engine venv had DuckDB 1.5.4 against a 2.0.0 lock, `make test` stopped on Node 26 before pytest, and the full suite has two failures outside this diff.

## Creative Phase Review

Check-pass retention held. `started_at` is the swap clock, the inode check keeps a hard link of the live file, and mtime, access time, and newer rows stayed out of the predicate. The guide's "never deletes" sentence was the contract that had to change, and it did.

Time-boxed check held after the operator narrowed it. The first design launched for any present backup. That would have started a child for every young swap, which is the session the quiet-hook goal exists to skip. The revision — launch only when the unlink predicate is already true — is what made the two creative decisions fit together. Putting the gate in the parent, and refusing a shell copy of `resolve_home`, avoided a second home resolver.

The creative notes did not flag that the two call sites need different answers to `OSError`. The second preflight did.

## Build & QA Observations

The red runs failed for the reason TDD wanted: the backup was still there, and the quiet parents still launched. After the gate, `test_check.py` was 75 passed. A first full run of that file failed on storage version `v2.0.0` because `pytest --no-sync` does not upgrade the venv. `uv sync --frozen --inexact` installed DuckDB 2.0.0. Torch was not in that venv, so the inexact sync did not strip it.

`make test` needs Node 22. The `node` on PATH is 26, and the dashboard target exits before pytest. Node 22 from nvm ran the suite: dashboard JS 134 passed; pytest 1228 passed, 6 skipped, 2 failed. Those two failures are the dashboard identity resolving `/tmp` to `/private/tmp`, and a stale root docs lock. This diff does not touch either.

QA passed. It left two optional notes: a comment in `test_check.py` that repeats a docstring, and the restore steps, which still tell the reader not to run writers during the rename window. After the 14 days, a new session in that window can remove the backup. The paragraph above the steps already says to restore before then. Neither note blocks.

## Cross-Phase Analysis

The first preflight passed a gate the operator then rejected. The cost was a second plan and a second preflight, not a wrong build. The second preflight's "one predicate" advisory is why the gate and the unlink cannot drift. The build then had to let `OSError` propagate: if the helper returned false on that error, the child the parent had started in order to reclaim would leave the file.

The pre-mortem named the two guide sentences that claimed the backup is never removed. The prose step changed both. QA's leftover is a third sentence in the same procedure, the one about not running writers. A retention deadline makes every "leave this session running" step in that procedure a race, not only the sentence that says the file stays forever.

## Insights

### Technical

- A predicate shared by a launcher and an unlink must raise `OSError`. The launcher treats the error as "start the child." The unlink treats it as "leave the name." Swallowing the error inside the helper picks one of those and silently drops the other.
- `make test` checks Node before pytest. A newer `node` on PATH hides the engine results. This machine's Node 22 is the nvm binary, passed as `NODE`.

### Process

- When the operator changes a gate after preflight, retire that status and preflight the new plan. The first pass had approved "any backup file launches," which is the behavior the revision exists to remove.
- A quiet-import rule decides which module may own a string. The backup name could not stay on `doctor`, because the parent would have imported DuckDB to read it.
