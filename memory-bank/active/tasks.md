# Task: Soak clock starts when the new warehouse is live

* Task ID: fortnight-backup-and-quiet-check
* Complexity: Level 2
* Type: bug fix

The 14-day unlink reads `swapped_at`, stamped when the record becomes `swapped`. Phase B `started_at` stays the four-hour alarm clock. A swapped record with no `swapped_at` is stamped on the stop path and kept for 14 days from that stamp, so a warehouse that already swapped still gets the soak.

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
- Late resume: phase B links, the replace fails, and a pass 15 days after `started_at` finishes the swap → status `swapped`, `started_at` unchanged, `swapped_at` is the resume `now`, backup remains.
- Quiet parent: `swapped_at` one second under 14 days → `main` does not call `launch`.
- Due parent: `swapped_at` exactly 14 days old, inodes differ → `main` calls `launch` and does not call `entry`.
- Unstamped parent: version 1 `swapped`, `swapped_at` absent, `started_at` a fortnight old → `main` calls `launch`.
- Bool parent: `swapped_at` is `true` → `main` does not call `launch`.

### Test Infrastructure

- Framework: pytest, as configured in `skills/sr-search/pyproject.toml`
- Test location: `skills/sr-search/tests/test_check.py`
- Conventions: one behavior per test, docstring is the behavior, `now` is injected, homes are `tmp_path`. Parent tests monkeypatch `check.launch` and `check.entry` and freeze `check.time.time`.
- New test files: none

## Implementation Plan

### 1. Unlink from `swapped_at` — executable

- Files: `skills/sr-search/src/stockroom/check.py`, `skills/sr-search/tests/test_check.py`

1. Stub tests: retarget the young, deadline, same-inode, second-pass, and parent young/due/same-inode tests so the fortnight is `swapped_at`. Add empty tests for the old `started_at`, the absent `started_at`, the bool `swapped_at`, and the bool parent. Point `test_reclaim_bool_started_at_keeps_the_backup` and `test_parent_bool_started_at_returns` at `swapped_at`.
2. Stub interface: add `swapped_at: float | None = None` to `_outcome`, stored on the record. `_swap_backup_due` keeps its signature. Its docstring names `swapped_at` as the soak clock and `started_at` as not that clock.
3. Write tests and run red: `_finished_pair` gains `swapped_at`. Deadline helpers use it. The old-clock test sets `started_at` to `_STARTED_AT` and `swapped_at` to the run's `now`. The bool tests set `swapped_at` to `True` and `started_at` to `_STARTED_AT`. `test_record_round_trip` expects `swapped_at: None`. Run those tests and confirm the deadline and old-clock cases fail.
4. Write code and run green: `_swap_backup_due` reads `swapped_at` with the same rules it used for `started_at` (not a bool, int or float, `now >= swapped_at + SWAP_BACKUP_RETENTION_SECONDS`, both files, inodes differ). A missing `swapped_at` is false. The retention comment names `swapped_at`. Run the retargeted tests.

### 2. Stamp `swapped_at` when the record becomes `swapped` — executable

- Files: `skills/sr-search/src/stockroom/check.py`, `skills/sr-search/tests/test_check.py`

1. Stub tests: extend `test_phase_b_swaps_in_a_new_copy` to expect `swapped_at` equal to that pass's `now`. Add an empty resume test.
2. Stub interface: `_finish_swap(home, record, *, backup_name, now: float) -> None`. Docstring says both swapped writes set `swapped_at` to `now` and leave `started_at` as it was.
3. Write tests and run red: `test_failed_replace_resumes_from_linked` keeps its first pass. The new resume test fails the replace, then runs again at `started_at + 15 days`. It expects `swapped_at` to be that later `now`, `started_at` unchanged, and the backup still present. Run it and confirm `swapped_at` is missing.
4. Write code and run green: `_phase_b` sets `swapped["swapped_at"] = now()` on the swapped record. `_acquired` passes `now()` into `_finish_swap`. Both swapped writes in `_finish_swap` set `swapped_at` to that `now`. Run the resume test and the phase B assertion.

### 3. Stamp a swapped record that has no soak time — executable

- Files: `skills/sr-search/src/stockroom/check.py`, `skills/sr-search/tests/test_check.py`

1. Stub tests: empty tests for the missing-soak reclaim, the second pass one second later, and the unstamped parent.
2. Stub interface: `_stamp_swapped_at(home, record, *, now: float) -> dict` writes `swapped_at` when the key is missing or the value is `None`, and returns the record it wrote. A bool or any other value is left in place. Docstring says this does not unlink.
3. Write tests and run red: a fortnight-old `started_at` and no `swapped_at` → `run_check` at the deadline keeps the backup and sets `swapped_at` to that `now`. One second later the backup and `swapped_at` stay. `main` on that unstamped home calls `launch`. `test_parent_missing_started_at_returns` changes with this: no `swapped_at` launches. Run the new tests and confirm the stamp is absent and the parent does not launch.
4. Write code and run green: on `stop` for `swapped`, when `swapped_at` is missing or `None`, call `_stamp_swapped_at` and return before the unlink. `_needs_child` returns true for version 1 `swapped` when `swapped_at` is missing or `None`. A bool still follows `_swap_backup_due` and does not launch. Run these tests, then `tests/test_check.py`.

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

- A missing `swapped_at` that the parent treats as quiet never gets stamped, and the backup stays forever. The unstamped-parent test expects `launch`. The child is the only writer.
- Stamping a bool would erase the value the bool test keeps. `_stamp_swapped_at` writes only for a missing key or `None`.
- `_finish_swap` has no clock today. Passing `now()` from `_acquired` keeps the resume test's injected clock. A private `time.time()` inside `_finish_swap` would ignore that injection.
- A frozen `now()` makes phase B's `started_at` and `swapped_at` equal. That pass cannot show the gap. The resume test uses a second clock 15 days later.
- Backfill changes raw `check.json` bytes. Deadline tests that assert unchanged bytes must already carry `swapped_at`, or they take the stamp path and fail.
- Falling back to `started_at` when `swapped_at` is absent would bring the late-resume bug back for any record the stamp missed. There is no fallback.

## Pre-Mortem

- The predicate still unlinks from `started_at`. The old-clock test is the one that goes red, and unit 1 does not finish until it stays green.
- The stamp and the unlink run in one stop pass, so a fortnight-old `started_at` loses the backup while the stamp is written. Unit 3 returns after the stamp, and the missing-soak test expects the backup to remain.
- `_finish_swap` writes `swapped` and forgets `swapped_at`. The next session's backfill would start the 14 days one session late. Unit 2 still sets it on both swapped writes, and the resume test reads that value. The backfill covers a record that already reached `swapped` without the field.

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Pre-Mortem complete
- [ ] Preflight
- [ ] Build
- [ ] QA
