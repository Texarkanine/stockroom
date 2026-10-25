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
2. Replace only the warehouse-check sentence on that same bullet. State all of these:
    - On an eligible existing warehouse, the first run rehearses a copy. At least one day later, a session start that still finds the warehouse eligible replaces the file and keeps the original under a backup name.
    - A warehouse that is already in the new format is recorded as already new. The check does not rehearse it and does not replace it.
    - Eligible is defined in the troubleshooting warehouse section. Link that section.
3. Do not say that every warehouse which is not already new is rehearsed or replaced. `_readiness` does not copy a missing file, a file with `warehouse.duckdb.wal`, a stockroom home on a read-only filesystem, a schema below version 9, or a file with free disk under twice the live size plus 64 MiB.
4. Keep the trailing Dashboard link.

### 3. Troubleshooting restore — prose/policy

- Files: `docs/user-guide/troubleshooting/index.md`
- No tests: prose/policy artifact

1. Replace the `## Warehouse` section through the four numbered steps. Do not edit `## Still stuck`.
2. Write the section in the spirit of ASD-STE100: short sentences, active voice, one meaning per word. Keep these names: `warehouse.duckdb`, `warehouse.duckdb.wal`, `warehouse.issue147-swap.duckdb`, `already-new`, `swapped`, `linked`, `running`, `overrun`, `check.json`, `stockroom doctor probe`.
3. Put these three blocks before any numbered step, in this order.
    - When this applies. The reader wants the original warehouse back. The rename applies when `warehouse.issue147-swap.duckdb` is in the same directory as `warehouse.duckdb`. A new-format warehouse is recorded `already-new`. The check does not rehearse it and does not replace it. A `backup` value of `absent` means the rename does not apply. An `overrun` value with no backup file is not a rename. Delete `check.json` only.
    - The problem. The check rehearses only an eligible warehouse. Eligible means all of these: the warehouse file is present, no `warehouse.duckdb.wal` is beside it, the stockroom home is not on a read-only filesystem, the schema version is 9 or above, free disk is at least twice the live size plus 64 MiB, and the file is not already in the new format. On an eligible warehouse, the first run makes a copy and then deletes that copy. At least one day later, a session start that still finds the warehouse eligible replaces `warehouse.duckdb` with a verified copy and leaves the original as `warehouse.issue147-swap.duckdb`. Stockroom does not delete that file. The backup name can exist before the record is `swapped`. While the record is `linked`, the check can put the new copy on `warehouse.duckdb`. The reader does not rename in that window. Some records never become `swapped`.
    - The solution. Rename only when the first word of the check value is `swapped` and the first word of the warehouse value is not `busy`. The replacement has already happened. The live file is the verified copy. A `swapped` record does not replace that file again. The reader renames the files. Stockroom does not rename them. A `busy` warehouse value means wait, including when the check value is `swapped`. A `linked` value needs one new session, because that session is what can write `swapped`. Do not start a second session. After every new probe, read the three first words from that probe, then start at the wait branch. Stop on a not-busy `linked` value only after a probe taken since that session has shown `busy`, or after 300 seconds from that session. Forget a `busy` word from before the session. Do not say whether the live file is the original. An `overrun` value does not become `swapped`. If the backup file exists, move it aside, then delete `check.json`. If the backup value is `absent`, delete `check.json` and do not move a file. Do not use the rename steps for `overrun`.
4. Then give the steps, in this order. `format_facts` prints `key:` and then spaces and then the value. The value is the text after those spaces. The first word of the check value is the status word. Do not say that the characters immediately after the colon are that word. After every new probe, read the three first words from that probe, then start at the wait branch. Do not keep the words from the previous probe. A later probe does not jump to the rename. Do not tell the reader to wait for `swapped` with no new session. Keep the heading `## Warehouse`.
    1. Run `stockroom doctor probe`.
    2. Read the first word of the warehouse value, of the check value, and of the backup value from this probe. Ignore the spaces after each colon.
    3. If the check value's first word is `running`, or the warehouse value's first word is `busy`, wait, run step 1 again, then run step 2 on that new probe, then continue from step 3. Do not rename.
    4. If the check value's first word is `overrun` and the backup value's first word is `absent`, delete `check.json`. Do not move a backup file. Stop. Do not rename.
    5. If the backup value's first word is `absent`, stop. The rename does not apply.
    6. If the check value's first word is `overrun`, move `warehouse.issue147-swap.duckdb` aside. Delete `check.json` in that same directory. Stop. Do not rename `warehouse.duckdb`.
    7. If the check value's first word is `linked`, use one session only. If you have not started a session for this restore, start one session. Then run step 1 again, run step 2 on that new probe, and continue from step 3. Do not start a second session. The 300 seconds start when that session starts. A `busy` word counts only on a probe read after that session. Forget a `busy` word from before the session. If you have started that session, and no probe since the session has shown `busy`, and fewer than 300 seconds have passed since the session, wait, run step 1 again, run step 2 on that new probe, and continue from step 3. If you have started that session, and a probe since the session has shown `busy` or 300 seconds have passed since the session, and the warehouse value's first word on this probe is not `busy`, and the check value's first word on this probe is still `linked`, stop. Do not rename.
    8. If the check value's first word is `swapped` and the warehouse value's first word is not `busy`, stop writers (do not run ingest, embed, or the nightly job), read the path in the backup value, rename `warehouse.duckdb` to a name of the reader's own, then rename the backup file to `warehouse.duckdb`. Do not start a session during those renames.
    9. If the check value's first word is any other word, stop. Do not rename.

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
2. Otherwise post one reply with `gh`, `in_reply_to` `4371593291`. The reply is limited to a version-1 `started` object. It says: this check writes `check_version` 1, `started_at`, and `limit_seconds`, and `write_record` stores the whole object. `next_action` reads the time fields only when `check_version` is 1. On that object, a missing field raises `KeyError` and a value that cannot be added raises `TypeError`, in both `check_line` and `next_action`. That child dies before phase A. `check_line` still raises on that object, so `doctor probe` still raises. A `try`/`except` only in `check_line` does not change that child. An object whose `check_version` is missing or is not 1 makes `next_action` return `phase-a`, including `{"status": "started"}`. Readiness can still skip the copy on that path. End with `Disposition: dismiss. No code change.`
3. Do not reply to the full-flush nit or to the comments that this plan fixes in docs.

## Technology Validation

No new technology - validation not required

## Dependencies

- Existing pytest suite for the doctor regression
- `gh` authenticated as a user who can comment on `Texarkanine/stockroom` pull request 152

## Challenges & Mitigations

- The quickstart edit can disturb the "click here!" link: the work step keeps the link token byte for byte and replaces only the check sentence.
- The troubleshooting rewrite can drop `already-new`, the eligible skips, or the backup path: the section outline requires all three before the steps are done.
- A reader who waits for `swapped` and never starts a session stays on a stopped `linked` record: step 7 of the restore starts one session, and a not-busy `linked` value after that session's clock is a stop, not a rename.
- The `overrun` reader uses the swap renames: step 4 deletes `check.json` when the backup value is `absent`, and step 6 moves the backup aside and deletes `check.json` when the backup file exists.
- The GitHub reply can duplicate or land on the wrong thread: post only when `4371593291` has no `Texarkanine` reply, and set `in_reply_to` to that id.
- The pre-commit hook's exact sync removes torch from this live checkout: after each commit, run `stockroom shim ensure-env`.
- `memory-bank/active/` is on the release branch again: the capstone archive is what removes it. Do not delete it in this task.

## Pre-Mortem

- The plan is carried out as a change to `_finish_swap`: the brief and step 3 forbid a state-machine edit. The restore is documentation.
- The old comment "Report it" is implemented as a new probe fact: step 4 deletes the comment and adds no fact. The existing below-head test is the guard.
- A reader still renames while the record is `linked` because the steps come first: step 3 puts the situation, the problem, and the solution before the numbered list, and the list renames only from a `swapped` value that is not busy.
- A busy `swapped` reader matches no step: the wait branch includes every `busy` warehouse value, and a later probe starts at that branch.
- An `overrun` with no backup file never deletes `check.json`: the absent-backup stop is after the overrun-and-absent delete.
- The reader treats aligning spaces as part of the status word: the steps say the value is the text after those spaces, and the comparison uses the first word.
- The page grows a new restore command that takes the writer flock: declined. That command is a different task. This page carries the branches until such a command exists.
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
