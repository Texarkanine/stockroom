# Task: Soak clock starts when the new warehouse is live

* Task ID: fortnight-backup-and-quiet-check
* Complexity: Level 2
* Type: bug fix

The 14-day unlink reads `swapped_at`, stamped when the record becomes `swapped`. Phase B `started_at` stays the four-hour alarm clock. A swapped record with no `swapped_at` is stamped on the stop path only when the backup and the live warehouse are both files and their inodes differ, and that backup is kept for 14 days from the stamp. The Rework section of the brief replaces the original clauses that measure those 14 days from `started_at`. Acceptance criteria 7 and 12 stay.

## Test Plan (TDD)

### Behaviors to Verify

- Young soak: version 1 `swapped`, numeric `swapped_at`, `now` one second under 14 days, two distinct files → backup remains, warehouse bytes unchanged, raw `check.json` unchanged.
- Deadline: same setup at exactly `swapped_at + 14 * 86400` → backup name is gone, warehouse bytes unchanged, raw `check.json` unchanged.
- Same inode: backup name is a hard link of `warehouse.duckdb`, `swapped_at` a fortnight old → backup name remains, raw `check.json` unchanged.
- Old alarm clock: `started_at` is `_STARTED_AT`, `swapped_at` equals the run's `now`, and that `now` is `_STARTED_AT + 14 days` → backup remains, raw `check.json` unchanged.
- Alarm clock absent: `started_at` omitted, `swapped_at` a fortnight old → backup is removed, raw `check.json` unchanged.
- Bool soak: `swapped_at` is `true` and `started_at` is a fortnight old → backup remains, raw `check.json` unchanged.
- Missing soak: version 1 `swapped`, no `swapped_at`, `started_at` a fortnight old → backup remains, and the record's `swapped_at` is that run's `now`.
- Second pass: one second after that stamp → backup remains, `swapped_at` unchanged.
- Late resume, replace failed: phase B links, the replace fails, and a pass 15 days after `started_at` finishes the swap → status `swapped`, `started_at` unchanged, `swapped_at` is the resume `now`, backup remains.
- Late resume, replace landed: the replace lands and the `swapped` write does not, and a pass 15 days after `started_at` records `swapped` → `swapped_at` is that later `now`, `started_at` unchanged, backup remains.
- Quiet parent: `swapped_at` one second under 14 days → `main` does not call `launch`.
- Due parent: `swapped_at` exactly 14 days old, inodes differ → `main` calls `launch` and does not call `entry`.
- Unstamped parent: version 1 `swapped`, `swapped_at` absent, both files, inodes differ → `main` calls `launch`.
- No backup: version 1 `swapped`, `swapped_at` absent, backup not a file → `main` does not call `launch`.
- No live warehouse: version 1 `swapped`, `swapped_at` absent, backup present, live warehouse missing → `main` does not call `launch`.
- Same inode, no soak time: `swapped_at` absent, backup name hard-linked to the live warehouse → `main` does not call `launch`, and `run_check` does not write `swapped_at`.
- Bool parent: `swapped_at` is `true` → `main` does not call `launch`.

### Test Infrastructure

- Framework: pytest, as configured in `skills/sr-search/pyproject.toml`
- Test location: `skills/sr-search/tests/test_check.py`
- Conventions: one behavior per test, docstring is the behavior, `now` is injected, homes are `tmp_path`. Parent tests monkeypatch `check.launch` and `check.entry` and freeze `check.time.time`.
- New test files: none

## Implementation Plan

### 1. Unlink from `swapped_at` — executable

- Files: `skills/sr-search/src/stockroom/check.py`, `skills/sr-search/tests/test_check.py`

1. Stub tests: retarget the young, deadline, same-inode, second-pass, and parent young/due/same-inode tests so the fortnight is `swapped_at`. Add empty tests for the old `started_at`, the absent `started_at`, the bool `swapped_at`, and the bool parent. Point `test_reclaim_bool_started_at_keeps_the_backup` and `test_parent_bool_started_at_returns` at `swapped_at`. Add `swapped_at` to two fixtures that must keep their current meaning: `test_importing_check_on_a_young_swap_does_not_import_duckdb` gets `swapped_at` equal to its young `started_at`, and `test_parent_stat_error_on_a_due_backup_starts_the_child` gets `swapped_at=_STARTED_AT`.
2. Stub interface: add `swapped_at: float | None = None` to `_outcome`, stored on the record. `_swap_backup_due` keeps its signature. Its docstring names `swapped_at` as the soak clock and `started_at` as not that clock.
3. Write tests and run red: `_finished_pair` gains `swapped_at`. Deadline helpers use it. The old-clock test sets `started_at` to `_STARTED_AT` and `swapped_at` to the run's `now`. The bool tests set `swapped_at` to `True` and `started_at` to `_STARTED_AT`. The rehearsed record `_rehearse` returns has `swapped_at is None`, because `_outcome` wrote it. Do not edit the hand-written dict in `test_record_round_trip`. Run those tests and confirm the deadline and old-clock cases fail.
4. Write code and run green: `_swap_backup_due` reads `swapped_at` with the same rules it used for `started_at` (not a bool, int or float, `now >= swapped_at + SWAP_BACKUP_RETENTION_SECONDS`, both files, inodes differ). A missing `swapped_at` is false. The retention comment and the `_needs_child` docstring name `swapped_at` as the soak clock. Run the retargeted tests.

### 2. Stamp `swapped_at` when the record becomes `swapped` — executable

- Files: `skills/sr-search/src/stockroom/check.py`, `skills/sr-search/tests/test_check.py`

1. Stub tests: extend `test_phase_b_swaps_in_a_new_copy` to expect `swapped_at` equal to that pass's `now`. Add an empty resume test for the failed replace. Extend `test_replace_that_lands_resumes_without_copying` so its resume pass takes a later clock.
2. Stub interface: `_finish_swap(home, record, *, backup_name, now: float) -> None`. Docstring says both swapped writes set `swapped_at` to `now` and leave `started_at` as it was.
3. Write tests and run red: `test_failed_replace_resumes_from_linked` keeps its first pass. The new resume test fails the replace, then runs again at `started_at + 15 days`. It expects `swapped_at` to be that later `now`, `started_at` unchanged, and the backup still present. `test_replace_that_lands_resumes_without_copying` keeps its first pass, then runs the resume at `started_at + 15 days` and expects those same three outcomes. That is the branch where the inodes already differ. Run both and confirm `swapped_at` is missing.
4. Write code and run green: `_phase_b` sets `swapped["swapped_at"] = now()` on the swapped record. `_acquired` passes `now()` into `_finish_swap`. Both swapped writes in `_finish_swap` set `swapped_at` to that `now`, including the branch where the inodes already differ. Run both resume tests and the phase B assertion.

### 3. Stamp a swapped record that has no soak time — executable

- Files: `skills/sr-search/src/stockroom/check.py`, `skills/sr-search/tests/test_check.py`

1. Stub tests: empty tests for the missing-soak reclaim, the second pass one second later, and the unstamped parent.
2. Stub interface: `_stamp_swapped_at(home, record, *, now: float) -> None` writes `swapped_at` through `_write_outcome` when the key is missing or the value is `None`. A bool or any other value is left in place. A failed write does not raise. Docstring says this does not unlink.
3. Write tests and run red: a fortnight-old `started_at`, no `swapped_at`, both files, distinct inodes → `run_check` at the deadline keeps the backup and sets `swapped_at` to that `now`. One second later the backup and `swapped_at` stay. `main` on that home calls `launch`. `test_reclaim_missing_started_at_keeps_the_backup` becomes that stamp test: it no longer expects the raw record to stay unchanged. `test_parent_missing_started_at_returns` becomes the unstamped-parent launch, because that home has two distinct files and no `swapped_at`. Run the new tests and confirm the stamp is absent and the parent does not launch.
4. Write code and run green: on `stop` for `swapped`, when `swapped_at` is missing or `None` and the backup and the live warehouse are both files with different inodes, call `_stamp_swapped_at` and return before the unlink. `_stamp_swapped_at` writes through `_write_outcome` and returns `None`. A false write leaves the record unstamped and does not raise. `_needs_child` returns true for that same pair of files. It returns false when the backup is missing, the live warehouse is missing, or the inodes match, which keeps acceptance criteria 7 and 12. A bool still follows `_swap_backup_due` and does not launch. These existing tests stay as they are, because their homes have no distinct backup to stamp:
    - `test_final_swapped_record_deletes_a_leftover_sibling` has no backup file, so the raw record stays unchanged.
    - `test_launch_on_a_swapped_record_does_not_build` has no backup file, so the loaded record stays equal to the one it wrote.
    - `test_parent_finished_without_a_backup_returns` has no backup file, so the swapped case still does not launch.
    - `test_parent_missing_warehouse_returns` has no live warehouse, so it still does not launch.
    A same-inode home with no `swapped_at` does not launch and `run_check` does not write the field. `OSError` from those file checks starts the child, the same way `_swap_backup_due` does. On the stop path the same `OSError` is caught, the record is left as it is, and the pass does not raise, the same way `_reclaim_swap_backup` treats `OSError`. Run these tests, then `tests/test_check.py`.

### 4. User guide — prose/policy

- Files: `docs/user-guide/troubleshooting/index.md`
- No tests: prose/policy artifact

1. In the Warehouse overview, say the backup stays 14 days after the new warehouse is the one in use.
2. In "Put the original warehouse back", say the check removes the backup 14 days after the new warehouse is in use. Put the original back before then. A session during those 14 days does not remove the backup. A session after them can.
3. Leave the numbered steps as they are.

## Technology Validation

No new technology - validation not required.

## Dependencies

- `stockroom.check` already owns the record, the flocked pass, and `main`.
- `tests/test_check.py` already builds homes with `_finished_pair` and freezes the parent clock.

## Challenges & Mitigations

- A missing `swapped_at` that the parent treats as quiet never gets stamped, and a distinct backup stays forever. The unstamped-parent test expects `launch` only when both files exist and the inodes differ. The child is the only writer.
- Launching for every missing stamp would start a child when there is no backup or no live warehouse. Those homes stay quiet. The stamp on the stop path uses the same file check, so a direct `run_check` does not rewrite them either.
- Stamping a bool would erase the value the bool test keeps. `_stamp_swapped_at` writes only for a missing key or `None`.
- A raw `write_record` that raises crashes the child, and the next session launches again. `_write_outcome` already returns false on `OSError`. The stamp uses it.
- `OSError` from stating the backup or the live warehouse, on the new file check, starts the child. The stop path catches it and leaves the record, as `_reclaim_swap_backup` does.
- One shared `keep` / `stamp` / `unlink` answer for the parent and the child was considered and left out. The parent and the stop path each state the same file rule in this plan.
- One `_mark_swapped` helper for every `swapped` write was considered and left out. This rework sets `swapped_at` at the two finish sites and on the one backfill. A fourth writer is not added.
- `_finish_swap` has no clock today. Passing `now()` from `_acquired` keeps the resume test's injected clock. A private `time.time()` inside `_finish_swap` would ignore that injection.
- A frozen `now()` makes phase B's `started_at` and `swapped_at` equal. That pass cannot show the gap. The resume test uses a second clock 15 days later.
- Backfill changes raw `check.json` bytes. Deadline tests that assert unchanged bytes must already carry `swapped_at`, or they take the stamp path and fail.
- Falling back to `started_at` when `swapped_at` is absent would bring the late-resume bug back for any record the stamp missed. There is no fallback.

## Pre-Mortem

- The predicate still unlinks from `started_at`. The old-clock test is the one that goes red, and unit 1 does not finish until it stays green.
- The stamp and the unlink run in one stop pass, so a fortnight-old `started_at` loses the backup while the stamp is written. Unit 3 returns after the stamp, and the missing-soak test expects the backup to remain.
- `_finish_swap` writes `swapped` and forgets `swapped_at`. The next session's backfill would start the 14 days one session late, and only when a distinct backup exists. Unit 2 still sets it on both swapped writes, and the resume test reads that value. The backfill covers a record that already reached `swapped` without the field.
- The missing-stamp launch ignores the files and starts a child for a home with no backup. The no-backup and no-warehouse behaviors are in the test plan, and unit 3 launches only when both files exist and the inodes differ.

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Pre-Mortem complete
- [x] Preflight
- [x] Build
- [x] QA

## QA Results (2026-10-28, second run) — PASS

- Reviewed `4503ab5..fc3383c`. `tests/test_check.py`: 82 passed. Ruff check and format: clean.
- B1 is fixed. The four retargeted tests now state `swapped_at` and their assertion. The `started_at` names that remain belong to tests about `started_at`.
- A1 to A3 are applied: `_outcome` drops the parameter and no caller passes it, the docstring is reflowed, and the lifecycle doc names the stamp child.
- Advisory: `_stamp_swapped_at` keeps the redundant guard the plan asked for. It does not block.

## QA Results (2026-10-28) — FAIL

- `tests/test_check.py`: 82 passed. Ruff check and format: clean. Every planned behavior has a test, and units 1-4 match the plan.
- Blocking B1: `test_parent_missing_started_at_returns` asserts a launch, and its name says the parent returns. Rename it and the other three retargeted tests that still name `started_at`: `test_reclaim_missing_started_at_keeps_the_backup`, `test_reclaim_bool_started_at_keeps_the_backup`, and `test_parent_bool_started_at_returns`.
- Advisory A1: drop the unused `swapped_at` parameter on `_outcome` (preflight A4).
- Advisory A2: reflow line 8 of the `check.py` module docstring.
- Advisory A3: `docs/architecture/lifecycle.md` should say that an unstamped distinct backup starts one child.
- Advisory A4: `_stamp_swapped_at` re-checks its guard. The plan asked for this, so it is acceptable.
