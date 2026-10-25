# Task: warehouse-check-review-wording

* Task ID: warehouse-check-review-wording
* Complexity: Level 2
* Type: simple enhancement

Make the warehouse-check sentences on pull request 152 true, rewrite the troubleshooting restore so the reader has the situation, the problem, and the solution before the steps, delete the dead schema-head comparison, and dismiss the malformed-record review comment. Do not change the check state machine or `os.fsync`.

## Test Plan (TDD)

### Behaviors to Verify

No new executable behavior.

- Existing contract: `stockroom doctor probe` on a warehouse whose `schema_version` is 1 → probe does not raise, does not change the file bytes, does not change `schema_version`, and still returns `warehouse-bytes` and `disk-free`. No schema-lag fact is added.
- The deletion of `if current_version(con) < _latest_version(): pass` does not change that contract. A new test that the source omits `_latest_version` would be a change-detector. Do not add one.

### Test Infrastructure

- Framework: pytest, configured in `skills/sr-search/pyproject.toml`
- Test location: `skills/sr-search/tests/test_doctor.py`
- Conventions: one behavior per `test_storage_*` function, docstring states the contract, facts come back as a dict from the local `_storage` / `_probe` helpers
- New test files: none

## Implementation Plan

### 1. Lifecycle sentence — prose/policy

- Files: `docs/architecture/lifecycle.md`
- No tests: prose/policy artifact

1. In the hook-doctrine paragraph, replace the sentence "The hook command itself returns at once." with "The hook runs rectify and the dashboard, then starts the check and does not wait for that child."
2. Leave the rest of that paragraph, including "A detached child may run for minutes."
3. Leave the numbered session-start list as it is. It already says the child is detached and the hook does not wait for the check.

### 2. Quickstart qualification — prose/policy

- Files: `docs/user-guide/quickstart.md`
- No tests: prose/policy artifact

1. Keep the link token `[click here!](http://localhost:58008)` byte for byte.
2. Replace only the warehouse-check sentence on that same bullet. State both of these:
    - On an existing warehouse that is not already in the new format, the first run rehearses a copy, and a later session start replaces the file and keeps the original under a backup name.
    - A warehouse that is already in the new format is recorded as already new. The check does not rehearse it and does not replace it.
3. Keep the trailing Dashboard link.

### 3. Troubleshooting restore — prose/policy

- Files: `docs/user-guide/troubleshooting/index.md`
- No tests: prose/policy artifact

1. Replace the `## Warehouse` section through the four numbered steps. Do not edit `## Still stuck`.
2. Write the section in the spirit of ASD-STE100: short sentences, active voice, one meaning per word. Keep these names: `warehouse.duckdb`, `warehouse.issue147-swap.duckdb`, `already-new`, `swapped`, `linked`, `stockroom doctor probe`.
3. Put these three blocks before any numbered step, in this order:
    - When this applies. The backup file `warehouse.issue147-swap.duckdb` is in the same directory as `warehouse.duckdb`, and the reader wants the original warehouse back. A new-format warehouse is recorded `already-new`. The check does not rehearse it and does not replace it. This restore does not apply to that warehouse.
    - The problem. On an older warehouse, the first check run makes a copy and then deletes that copy. A later session start replaces `warehouse.duckdb` with a verified copy and leaves the original as `warehouse.issue147-swap.duckdb`. Stockroom does not delete that backup. The backup name exists while the check record can still be `linked`. A `linked` check can put the new copy onto `warehouse.duckdb` during a rename.
    - The solution. Put the original back only after the check has stopped and `stockroom doctor probe` shows `swapped`. A `swapped` record does not replace `warehouse.duckdb`. The reader renames the files. Stockroom does not rename them.
4. Then give the steps, in this order:
    1. Run `stockroom doctor probe`.
    2. Read the `check` line. Wait until it shows `swapped`. If the probe shows `warehouse: busy`, a writer still holds the lock. Wait, then probe again. Do not start a new session until the rename is finished. A new session starts another check.
    3. Stop writers before the rename. Do not run ingest, embed, or the nightly job during the rename.
    4. Read the backup path on the `backup` line.
    5. In that directory, rename `warehouse.duckdb` to a name of the reader's own.
    6. Rename the backup file to `warehouse.duckdb`.

### 4. Dead schema-head comparison — executable

- Files: `skills/sr-search/src/stockroom/doctor.py`
- Existing test: `skills/sr-search/tests/test_doctor.py::test_storage_below_head_does_not_change_the_file`

1. Stub tests: no new test and no edit to the existing test. That test already asserts the observable contract.
2. Stub interface: no new function and no signature change.
3. Write tests and run red: do not add a test. Before the edit, run the existing test and confirm it is green. A red run is not expected, because the `pass` body has no outcome to withhold.
4. Write code and run green: delete the `if current_version(con) < _latest_version():` block and its comment. Delete `from stockroom.migrate import current_version` if nothing else in the file uses it. Delete `_latest_version` from the `stockroom.warehouse` import if nothing else in the file uses it. Leave `storage = tags["storage_version"]` and `reclaimable = size - live_bytes(con)`. Run the same test again. It stays green, and the returned facts still have no schema-lag key.

### 5. Dismiss the malformed-record comment — prose/policy

- Files: none in the tree. GitHub pull request 152, review comment `4371593291`.
- No tests: prose/policy artifact

1. If `Texarkanine` has already replied to comment `4371593291`, stop. Do not post a second reply.
2. Otherwise post one reply with `gh`, `in_reply_to` `4371593291`. The reply says: a `started` record written by this check always has `started_at` and `limit_seconds`; `write_record` publishes the whole object; an object that lacks those fields does raise, and the detached child exits on the same object in `next_action` without starting phase A; a `try`/`except` only in `check_line` would not fix the child and would hide a writer bug. End with `Disposition: dismiss. No code change.`
3. Do not reply to the full-flush nit or to the comments that this plan fixes in docs.

## Technology Validation

No new technology - validation not required

## Dependencies

- Existing pytest suite for the doctor regression
- `gh` authenticated as a user who can comment on `Texarkanine/stockroom` pull request 152

## Challenges & Mitigations

- The quickstart edit can disturb the "click here!" link: the work step keeps the link token byte for byte and replaces only the check sentence.
- The troubleshooting rewrite can drop `already-new` or the backup path: the section outline requires both before the steps are done.
- The GitHub reply can duplicate or land on the wrong thread: post only when `4371593291` has no `Texarkanine` reply, and set `in_reply_to` to that id.
- The pre-commit hook's exact sync removes torch from this live checkout: after each commit, run `stockroom shim ensure-env`.
- `memory-bank/active/` is on the release branch again: the capstone archive is what removes it. Do not delete it in this task.

## Pre-Mortem

- The plan is carried out as a change to `_finish_swap`: the brief and step 3 forbid a state-machine edit. The restore is documentation.
- The old comment "Report it" is implemented as a new probe fact: step 4 deletes the comment and adds no fact. The existing below-head test is the guard.
- A reader still renames while the record is `linked` because the steps come first: step 3 puts the situation, the problem, and the solution before the numbered list, and the list waits for `swapped`.
- Pull request 152 is merged while `memory-bank/active/` is present, so `main` is no longer a fresh Niko checkout: already covered by the challenge. Archive stays a later operator step.

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Pre-Mortem complete
- [ ] Preflight
- [ ] Build
- [ ] QA
