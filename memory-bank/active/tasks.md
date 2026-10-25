# Task: warehouse-check-review-wording

* Task ID: warehouse-check-review-wording
* Complexity: Level 2
* Type: simple enhancement

Make the warehouse-check sentences on pull request 152 true, rewrite the troubleshooting restore so the reader has the situation, the problem, and the solution before the steps, delete the dead schema-head comparison, and dismiss the malformed-record review comment. Do not change the check state machine or `os.fsync`.

The prose units below carry the exact text to ship. Five preflights failed a plan that described the restore page by rules. This plan gives the page itself.

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

1. In the hook-doctrine paragraph, replace "The hook command itself returns at once." with:

   > The hook command waits for rectify and the dashboard launch, then starts the check as a detached child and returns without waiting for it.

2. Leave the rest of that paragraph and the numbered session-start list as they are.

### 2. Quickstart qualification — prose/policy

- Files: `docs/user-guide/quickstart.md`
- No tests: prose/policy artifact

1. Replace the `sr-dashboard` bullet with the text below. The dashboard sentence, the `[click here!](http://localhost:58008)` token, and the `[Dashboard](dashboard.md)` link are byte for byte as they are now. Only the warehouse-check sentence changes, and it gains a link to the troubleshooting section.

   ~~~markdown
   - Open the local metrics UI with **`sr-dashboard`** (also launched automatically on session start - [click here!](http://localhost:58008) - when hooks are registered) — [Dashboard](dashboard.md). Session start also checks the warehouse file. When it is safe to do so, the check moves an older warehouse to the new storage format in two steps: a trial copy first, then, at least a day later, a verified copy that takes its place, with the original kept under a backup name. A warehouse that already uses the new format is left as it is — [Warehouse](troubleshooting/index.md#warehouse).
   ~~~

### 3. Troubleshooting restore — prose/policy

- Files: `docs/user-guide/troubleshooting/index.md`
- No tests: prose/policy artifact

1. Replace the `## Warehouse` section, from its heading through the four numbered steps, with the text below. Do not edit `## Still stuck`.

   ~~~markdown
   ## Warehouse

   Session start runs a check on the warehouse file. The check runs in the background and does not ask first.

   If the warehouse uses the older storage format, the check makes a trial copy in the new format, verifies it, and deletes it. At least one day later, a session start makes a new verified copy and puts it in place of `warehouse.duckdb`. The check keeps the original file in the same directory as `warehouse.issue147-swap.duckdb`. Stockroom never deletes that file.

   The check copies only when it can do so safely. For example, if free disk is low, a database write is not complete, or an ingest has not yet brought the warehouse to the current schema, the check does nothing and tries again at a later session start. A warehouse that already uses the new format is recorded as `already-new`. The check does not copy it or replace it.

   ### Put the original warehouse back

   **When this applies.** You want the warehouse as it was before the check replaced it. Run `stockroom doctor probe` and read the first word after `check:`.

   ```text
   warehouse:         /home/you/.local/share/stockroom/warehouse.duckdb
   backup:            /home/you/.local/share/stockroom/warehouse.issue147-swap.duckdb
   check:             swapped original_bytes=… path=…
   ```

   - `swapped`: the check replaced the warehouse. The original is the file on the `backup` line. Follow the steps below.
   - `running` or `linked`: a replacement can be in progress, or it stopped before it was complete. Follow the steps below. They let the check complete it first.
   - `absent`, `skip`, `rehearsed`, `already-new`, `mismatch`, or `overrun`: the check did not replace the warehouse. `warehouse.duckdb` is still the original. There is nothing to put back.
   - Any other word, including `unreadable`: do not rename a file. See [Still stuck](#still-stuck).

   These meanings are true only if nobody deleted `check.json`. If it was deleted, see [Still stuck](#still-stuck).

   **The problem.** While the word is `running` or `linked`, the check can still write to `warehouse.duckdb`. If you rename a file during that time, the check can replace it again. Also, a writer (ingest, embed, or the nightly job) that finds no `warehouse.duckdb` makes a new, empty one.

   **The solution.** Let the check complete, so that the word is `swapped`. After that, the check does not replace `warehouse.duckdb` again. Then stop all writers and exchange the two file names yourself. Keep `check.json` after the restore. It is the record that tells the check that the replacement is complete. If you delete it, a later session start can copy and replace the restored warehouse again.

   To put the original back:

   1. Run `stockroom doctor probe`. Find the `check` word in the list above, and do what that entry says.
   2. If the `check` word is `running`, wait. A copy of a large warehouse can take hours. Then go to step 1.
   3. If the `check` word is `linked`, start one new session in Cursor or Claude Code. Wait ten minutes. Then run `stockroom doctor probe` again.
       - If the `warehouse` line says `busy`, wait and run it again.
       - If the word is now `swapped`, go to step 4.
       - If the word is still `linked` and the `warehouse` line shows a path, stop. Do not rename a file. See [Still stuck](#still-stuck).
   4. Make sure that no writer runs during steps 5 to 8. Do not run `stockroom ingest`, `stockroom embed`, or the nightly job.
   5. Run `stockroom doctor probe`. If the `warehouse` line says `busy`, wait and run it again. Continue when the `warehouse` line shows a path.
   6. Go to the directory that contains the file on the `backup` line.
   7. Rename `warehouse.duckdb` to a name of your own, for example `warehouse.replaced.duckdb`. Do not use `warehouse.copy.duckdb`, because the check deletes a file with that name. If `warehouse.duckdb.wal` exists, rename it to your new name plus `.wal`.
   8. Rename `warehouse.issue147-swap.duckdb` to `warehouse.duckdb`.
   9. Run `stockroom doctor probe`. The `backup` line says `absent`, and the `check` word is still `swapped`.
   ~~~

2. Each claim and the code that makes it true:
    - Only `swapped` means replaced: `os.replace` runs only after `linked` is written, so `absent`, `skip`, `rehearsed`, `already-new`, `mismatch`, and an expired `started` (`overrun`) all leave the original as `warehouse.duckdb`. The exception is a `check.json` deleted after a swap, which the page names and sends to "Still stuck".
    - The problem paragraph is scoped to `running` and `linked`, the only words for which the check can still write `warehouse.duckdb`.
    - Below-boundary skips repeat until a writer `open()` migrates the warehouse, which the nightly ingest does.
    - The `check.json` warning is scoped to after the restore. At that point `warehouse.issue147-swap.duckdb` is gone, so a new phase B `os.link` can succeed.
    - `linked` completes on a later pass: `next_action` returns `finish-swap`, and `_finish_swap` writes `swapped` or leaves `linked`. A `linked` that stays `linked` is the uncommon case, so the page stops and sends the reader to "Still stuck".
    - After `swapped`, the check does not replace again: `next_action` returns `stop`, and `_acquired` only calls `_remove_sibling`.
    - `_remove_sibling` deletes `warehouse.copy.duckdb` and its `.wal` on every pass that is not `running` or `finish-swap`. That is why the replaced file must not take that name.
    - A writer `open()` of a missing warehouse builds a new one from the schema file. That is why writers stop during the renames.
    - A deleted `check.json` is no record, so `next_action` returns `phase-a`. That is why the record is kept.
    - Ten minutes is twice the 300-second hook timeout, and `_finish_swap` is a rename and a record write.
    - The probe example matches `format_facts`: a key, a colon, aligning spaces, then the value.

### 4. Dead schema-head comparison — executable

- Files: `skills/sr-search/src/stockroom/doctor.py`
- Existing test: `skills/sr-search/tests/test_doctor.py::test_storage_below_head_does_not_change_the_file`

1. Stub tests: no new test and no edit to the existing test. That test already asserts the observable contract.
2. Stub interface: no new function and no signature change.
3. Write tests and run red: do not add a test. Before the edit, run the existing test and confirm it is green. A red run is not expected, because the `pass` body has no outcome to withhold.
4. Write code and run green: delete the `if current_version(con) < _latest_version():` block and its comment. Delete `from stockroom.migrate import current_version` and `_latest_version` from the `stockroom.warehouse` import if nothing else in the file uses them. Leave `storage = tags["storage_version"]` and `reclaimable = size - live_bytes(con)`. Run the same test again. It stays green.

### 5. Dismiss the malformed-record comment — prose/policy

- Files: none in the tree. GitHub pull request 152, review comment `4371593291`.
- No tests: prose/policy artifact

1. If `Texarkanine` has already replied to comment `4371593291`, stop. Do not post a second reply.
2. Otherwise post this reply with `gh`, `in_reply_to` `4371593291`:

   ~~~markdown
   `check_line` does raise on a `started` record that has no `started_at` or `limit_seconds`, and `doctor probe` raises with it.

   This check never writes that record. Every `started` record comes from `_outcome`, which sets `check_version` 1, `started_at`, and `limit_seconds`, and `write_record` replaces `check.json` as a whole file. A record like that exists only if someone edits `check.json` by hand.

   For a version-1 `started` record, `next_action` reads the same two fields, so the detached check also fails on that record, before phase A. Catching the error only in `check_line` would make probe print `unreadable` while the check still fails. A traceback from probe is the more honest report of a hand-edited record.

   Disposition: dismiss. No code change.
   ~~~

3. Do not reply to the full-flush nit or to the comments that this plan fixes in docs.

## Technology Validation

No new technology - validation not required

## Dependencies

- Existing pytest suite for the doctor regression
- `gh` authenticated as a user who can comment on `Texarkanine/stockroom` pull request 152

## Challenges & Mitigations

- The quickstart edit can disturb the "click here!" link: unit 2 keeps the dashboard sentence byte for byte.
- The restore page can grow back into a decision table for every record state: the page lists four outcomes and sends uncommon states to "Still stuck". A state the page does not name is a stop, not a branch.
- The GitHub reply can duplicate or land on the wrong thread: post only when `4371593291` has no `Texarkanine` reply, and set `in_reply_to` to that id.
- The pre-commit hook's exact sync removes torch from this live checkout: after each commit, run `stockroom shim ensure-env`.
- `memory-bank/active/` is on the release branch again: the capstone archive is what removes it. Do not delete it in this task.

## Pre-Mortem

- The plan is carried out as a change to `_finish_swap`: the brief forbids a state-machine edit. The restore is documentation.
- The old comment "Report it" is implemented as a new probe fact: unit 4 deletes the comment and adds no fact.
- A reader renames into a name the check deletes: step 7 names `warehouse.copy.duckdb` and forbids it.
- A reader deletes `check.json` to "reset" things after the restore: the solution block says why the record stays.
- Pull request 152 is merged while `memory-bank/active/` is present: already covered by the challenge. Archive stays a later operator step.

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Pre-Mortem complete
- [ ] Preflight
- [ ] Build
- [ ] QA
