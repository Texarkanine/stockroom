# Task: Surgical embedding invalidation (#43)

* Task ID: surgical-embedding-invalidation
* Complexity: Level 2
* Type: simple enhancement

Stop cascade-deleting all session embeddings on ingest rewrite. In `write_session`, compare old vs new message texts and delete embeddings only for removed or text-changed `message_id`s; leave unchanged owners and other sessions alone. No schema migration; embed `NOT EXISTS` / `--full` unchanged.

## Test Plan (TDD)

### Behaviors to Verify

- Pure compare helper: removed id / changed text → invalidate; unchanged text and both-None → keep
- Unchanged rewrite: rewrite session with identical message texts → embeddings for those `message_id`s remain
- Append-only growth: rewrite with prior messages unchanged + new ordinals → prior embeddings retained; new ids have no vectors until embed
- Text change: same `message_id`, different `text` → that id's embeddings deleted; sibling unchanged ids retain theirs
- Message removal: rewrite omitting a prior `message_id` → that id's embeddings deleted
- Other sessions: rewrite session A → session B's embeddings never touched
- Multi-chunk owner: an owner with multiple `chunk_index` rows loses all chunks when its text changes (or id is removed)
- Regression: existing writer persistence / `first_seen_at` carry-forward tests stay green
- Embed contract unchanged: existing `test_embed.py` incremental `NOT EXISTS` / `--full` tests stay green (no code change expected)

### Test Infrastructure

- Framework: pytest (configured in `skills/sr-search/pyproject.toml`)
- Test location: `skills/sr-search/tests/`
- Conventions: module-scoped tests against `migrated_con` fixture; helpers `_session` / inline INSERT for fake embeddings; multi-line docstrings for non-obvious contracts
- New test files: none — extend/replace cases in `skills/sr-search/tests/test_ingest_writer.py`

## Implementation Plan

1. **Stub pure compare helper + replace cascade tests (failing)**
   - Files: `skills/sr-search/src/stockroom/ingest/writer.py`, `skills/sr-search/tests/test_ingest_writer.py`
   - Changes: Add empty/stub `_embedding_owner_ids_to_invalidate(old_texts, new_texts) -> set[str]` with docstring. Replace `test_rewriting_session_cascades_embedding_delete` with: (a) pure-helper unit cases for removed / changed / unchanged / both-None text; (b) integration cases via `write_session` for unchanged rewrite, append-only, text change (siblings retained), removal, other-session isolation, and multi-chunk invalidation. Shared `_add_embedding` helper. Expect failures until step 2.

2. **Implement compare-and-keep; strip blanket delete from `_delete_session`**
   - Files: `skills/sr-search/src/stockroom/ingest/writer.py`
   - Changes:
     - Implement `_embedding_owner_ids_to_invalidate`: ids in `old_texts` missing from `new_texts`, or present in both with unequal `text` (`None` equality as Python `==`).
     - When loading carry-forward state, also load `old_texts` (same query can select `message_id, text, first_seen_at`).
     - Build `new_texts` from `session.messages` via `_message_id`.
     - Before `_delete_session`, `DELETE FROM embeddings` for stale `owner_id`s only (`owner_table = 'messages'`, scoped by `harness`).
     - Remove the blanket embedding `DELETE` from `_delete_session`; update its docstring (children/messages/sessions only).
     - Update `write_session` / module docs to describe compare-and-keep invalidation instead of session-wide cascade.

3. **Docs: staleness / invalidation wording**
   - Files: `skills/sr-search/references/system-model.md`, `docs/architecture/embeddings.md`
   - Changes: In the embedding/staleness sections, note that re-ingest invalidates vectors only for removed or text-changed messages (append-only / unchanged history keeps embeddings), so embed lag after ingest leaves a small hole rather than wiping the session index. Do not invent soft-stale search policy.

4. **Verify**
   - Run targeted `test_ingest_writer` embedding cases, then full `make test` (or engine pytest suite) plus lint/format as required by project verification.

## Preflight Amendments

- Extract `_embedding_owner_ids_to_invalidate` as a pure helper so text-compare rules are unit-testable without DuckDB (preflight radical-innovation amendment; still within L2 / brief scope).

## Technology Validation

No new technology - validation not required

## Dependencies

- Existing `migrated_con` fixture and embeddings schema (`owner_table`, `owner_id`, multi-chunk PK)
- Issue #43 acceptance criteria as contract source
- Embed selection remains `NOT EXISTS` in `stockroom.embed` (no change)

## Challenges & Mitigations

- **NULL/`None` text compare**: Treat SQL NULL as Python `None`; equality keeps the vector, inequality invalidates. Cover via text-change and unchanged tests with non-null texts; optional NULL↔NULL keep is covered by Python `==` if a NULL text message exists in fixtures.
- **Delete before messages go away**: Surgical embedding delete must run while old message rows still exist only if we key by computed id lists — prefer deleting by explicit `owner_id IN (...)` from the compare result so order vs `_delete_session` is independent of message rows.
- **Doc drift vs archive**: Phase-2 archive still describes blanket cascade historically; do not rewrite archives. Update live system-model / architecture embeddings docs only.

## Pre-Mortem

- **Plan fails because we only change the happy-path test and leave blanket delete in `_delete_session`**: Step 2 explicitly removes that DELETE and step 1 asserts retention on unchanged rewrite — if either is skipped, CI catches it.
- **Plan fails by invalidating on non-text field changes (role/tokens) or by comparing wrong grain**: Contract is text-only at `message_id` grain per issue; tests rewrite with identical texts and expect retention even when delete-then-insert replaces rows.
- **Plan fails by updating only agent system-model and leaving human architecture docs wrong**: Step 3 lists both `system-model.md` and `docs/architecture/embeddings.md`.

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Pre-Mortem complete
- [x] Preflight
- [x] Build
- [ ] QA

### Build checklist

- [x] Step 1: Stub pure compare helper + replace cascade tests
- [x] Step 2: Implement compare-and-keep; strip blanket delete
- [x] Step 3: Docs (system-model + architecture embeddings)
- [x] Step 4: Verify (530 passed, 3 skipped; lint/format clean)
