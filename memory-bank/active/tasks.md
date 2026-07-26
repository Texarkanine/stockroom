# Task: PR #92 CodeRabbit feedback (selected fixes)

* Task ID: pr92-coderabbit-fixes
* Complexity: Level 2
* Type: simple enhancement (docs + adapter stability)

Land the nine operator-selected CodeRabbit findings from PR #92 review `4782519076`: seven documentation corrections and two `cursor_vscdb` stability fixes (`open_readonly` connection/URI hygiene; `candidates` → `BackfillError`). No creative-doc rewrites; dismissed nits stay dismissed.

## Test Plan (TDD)

### Behaviors to Verify

- **B1** (layout path base): read `backfill-adapters.md` → Layout section states paths are relative to `skills/sr-search/` (or every path is prefixed with that root).
- **B2** (typo): `docs/contributing/iteration/index.md` contains `section` and does not contain `secion`.
- **B3** (API token boundary): `cursor-vscdb.md` Reference states contemporary Cursor API tokens remain unavailable from `state.vscdb`.
- **B4** (grammar): Required Sequence step 1 does not say “all instance”; wording is grammatical (“every instance” / equivalent).
- **B5** (dry-run quit): `--dry-run` prose does not say “safe to rehearse at any time”; it still requires quitting the harness / acknowledges the store read can miss WAL-backed data while Cursor is open.
- **B6** (undo txn): Undoing A Run SQL includes `BEGIN` before the `doomed` create and `COMMIT` after the three deletes (same delete order).
- **B7** (`progress.md` lede): opening summary names the PR #92 / CodeRabbit rework (or load-section IA lineage), not the ADHD `ingest/backfill` pass as current — already done at rework initiation; re-verify only.
- **B8** (`open_readonly` closes failed rung): when `mode=ro` connect succeeds but the proving read fails, and `immutable=1` then succeeds → the abandoned `mode=ro` connection was closed; returned connection is usable. *(pytest)*
- **B9** (`open_readonly` URI-encodes path): a source path containing `?` still opens via the URI form (percent-encoded); monkeypatched `connect` sees an encoded URI, not a raw `?` before the mode query. *(pytest)*
- **B10** (`candidates` typed error): a readable SQLite file without `cursorDiskKV` → `candidates` raises `BackfillError` (not bare `sqlite3.Error`), message names the source. *(pytest)*
- **B11** (docs build): `make docs-build` exits 0 with zero warnings.

### Edge Cases

- `open_readonly`: both rungs fail after connect+execute failure — still `BackfillError`, no leaked connections if both were opened (close each failed rung).
- `candidates`: empty-but-valid `cursorDiskKV` still returns `[]` (no regression).
- Dry-run prose must keep “needs a warehouse / run ingest first” and “no write lock” — only the “any time” / quit-undercut language changes.
- Undo recipe: do not change delete order or `source_path` selection; only wrap in a transaction.

### Test Infrastructure

- Framework: pytest under `skills/sr-search/tests/`; docs via `make docs-build` (strict)
- Test location: extend `tests/test_backfill_cursor_vscdb.py` (existing `open_readonly` / `candidates` suite + `build_vscdb` fixture)
- Conventions: typed `BackfillError` assertions; monkeypatch `sqlite3.connect` for ladder tests (see `test_open_readonly_falls_back_to_immutable_when_mode_ro_fails`)
- New test files: none

## Implementation Plan

1. **Failing adapter tests (B8–B10)**
   - Files: `skills/sr-search/tests/test_backfill_cursor_vscdb.py`
   - Changes: add three tests — (a) `mode=ro` connect returns a connection whose proving `execute` fails, assert that connection’s `close()` was called when `immutable=1` succeeds; (b) path with `?` in the filename opens (or connect receives percent-encoded URI); (c) empty SQLite DB without `cursorDiskKV` → `candidates` raises `BackfillError`. Run → fail for the right reasons.
   - Verify: B8–B10 fail

2. **Implement `open_readonly` + `candidates` (B8–B10)**
   - Files: `skills/sr-search/src/stockroom/backfill/cursor_vscdb.py`
   - Changes:
     1. Build the URI with a percent-encoded path (`Path.resolve().as_uri() + "?" + mode`, or equivalent `urllib.parse.quote`); keep `uri=True`.
     2. On `sqlite3.Error` after a successful `connect`, `close()` that connection before continuing the ladder (and before the final raise).
     3. In `candidates`, wrap the `cursorDiskKV` query in `except sqlite3.Error` → `BackfillError` naming source + cause; keep the existing `finally: con.close()`.
   - Verify: B8–B10 pass; existing open_readonly / candidates tests still pass

3. **Docs: contributing (B1, B2)**
   - Files: `docs/contributing/iteration/backfill-adapters.md`, `docs/contributing/iteration/index.md`
   - Changes: one-line note under Layout that paths are relative to `skills/sr-search/`; `secion` → `section`.
   - Verify: B1, B2

4. **Docs: backfill user guide (B3–B6)**
   - Files: `docs/user-guide/load/backfill/cursor-vscdb.md`, `docs/user-guide/load/backfill/index.md`
   - Changes: API-token unavailability sentence in Reference; grammar on Required Sequence step 1; rewrite dry-run paragraph to retain quit-harness + warehouse-needed facts without “any time”; wrap undo SQL in `BEGIN;` … `COMMIT;`.
   - Verify: B3–B6

5. **Verify progress lede (B7) + strict docs build (B11)**
   - Files: `memory-bank/active/progress.md` (read-only unless still stale)
   - Changes: none expected (lede refreshed at rework initiation)
   - Verify: B7, B11 (`make docs-build`)

## Technology Validation

No new technology - validation not required. URI encoding uses stdlib (`pathlib.Path.as_uri` / `urllib.parse`) already imported in-module for workspace URLs.

## Dependencies

- Existing `test_backfill_cursor_vscdb.py` patterns and `build_vscdb` fixture
- ProperDocs strict build for doc gates
- Operator-selected item list only — creative docs and dismissed nits out of scope

## Challenges & Mitigations

- **`as_uri()` changes URI shape vs `file:{path}?mode=`**: existing monkeypatch tests match on `"mode=ro" in uri_string` / `"immutable=1" in uri_string` — substring checks still hold. If a test asserts the full URI prefix, update that assertion only.
- **Proving-read failure is harder to trigger than connect failure**: the leak path needs connect-ok + execute-fail; use a wrapper connection (or monkeypatch) rather than a real corrupt file, mirroring the existing ladder fake_connect style.
- **Dry-run copy can reintroduce the hazard while “fixing” grammar**: write the quit prerequisite into the dry-run paragraph explicitly; do not rely on Required Sequence alone.

## Pre-Mortem

- **We “fix” dry-run by only deleting “any time” and leave readers thinking warehouse lock safety = store-read safety**: already covered by Challenge 3 / B5’s positive assertion about quit/WAL.
- **URI encoding breaks the WSL mount path that made `immutable=1` necessary**: `as_uri()` is the stdlib form SQLite documents; re-run the existing immutable-fallback test as the regression gate.
- **Docs-only verification skips the adapter tests**: Step 2 explicitly re-runs the open_readonly/candidates suite before the docs steps count as done.

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Pre-Mortem complete
- [x] Preflight
- [x] Build
- [x] QA
- [x] Reflect
- [ ] Archive

## QA Results (2026-07-26)

✅ PASS — 1 trivial (docstring expanded for URI encode + close-on-fail); 0 substantive.

All nine selected review items present and verified. Out-of-scope dismissals untouched. Delete order in undo recipe unchanged (tool_calls → messages → sessions).

## Preflight Amendments (2026-07-26)

- None. TDD order is explicit (adapter tests → adapter impl → docs). `Path.as_uri()` percent-encodes `?`/`#` and preserves the substring assertions in existing ladder tests. No advisory redesign.

## Build Log (2026-07-26)

| Step | Outcome |
| --- | --- |
| 1. Failing adapter tests | 3 new tests red for the right reasons (leak unclosed; `?` path opens wrong DB; bare `OperationalError`) |
| 2. Implement open_readonly + candidates | Green; full adapter file 59/59 |
| 3. Contributing docs | B1, B2 |
| 4. Backfill user-guide docs | B3–B6 |
| 5. Lede + strict build | B7 already current; B11 green |

**Gates:** docs-build exit 0 / zero warnings; pytest 784 passed / 2 skipped; ruff clean.
