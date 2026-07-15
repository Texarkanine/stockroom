---
task_id: surgical-embedding-invalidation
complexity_level: 2
date: 2026-07-15
status: completed
---

# TASK ARCHIVE: Surgical embedding invalidation (#43)

## SUMMARY

Stopped cascade-deleting all session embeddings on ingest rewrite. `write_session` now compares old vs new message texts and deletes embeddings only for removed or text-changed `message_id`s; unchanged owners and other sessions are left alone. No schema migration; embed `NOT EXISTS` / `--full` unchanged. Satisfies [issue #43](https://github.com/Texarkanine/stockroom/issues/43).

## REQUIREMENTS

1. On session rewrite, compare old and new message texts before delete-then-insert.
2. Delete embeddings only for removed ids or ids whose text changed; retain unchanged `message_id`s.
3. Remove the blanket embedding delete from `_delete_session`.
4. Keep embed selection as-is (`NOT EXISTS` / `--full`); no schema migration.
5. Replace the old cascade test with a contract that locks retention and surgical invalidation.

**Constraints:** No soft-stale search; no content-hash column; no merging ingest+embed into one transaction; solution is compare-and-keep by text (issue option B).

## IMPLEMENTATION

Extracted pure `_embedding_owner_ids_to_invalidate(old_texts, new_texts) -> set[str]` (preflight amendment) so text-compare rules are unit-testable without DuckDB. In `write_session`, load old texts with carry-forward state, build `new_texts` from the session, surgically `DELETE` stale `owner_id`s (`owner_table = 'messages'`, harness-scoped via `UNNEST`), then proceed with existing `_delete_session` (children/messages/sessions only — no embeddings).

| Area | Files |
|------|--------|
| Writer | `skills/sr-search/src/stockroom/ingest/writer.py` |
| Tests | `skills/sr-search/tests/test_ingest_writer.py` |
| Docs | `skills/sr-search/references/system-model.md`, `docs/architecture/embeddings.md`, `memory-bank/systemPatterns.md` |

## TESTING

- TDD red→green: pure-helper unit cases plus integration cases for unchanged rewrite, append-only, text change (siblings retained), removal, other-session isolation, multi-chunk invalidation, empty-session clear.
- Full suite: **530 passed, 3 skipped**; lint/format clean.
- `/niko-preflight` PASS WITH ADVISORY (pure helper amendment applied).
- `/niko-qa` PASS — no substantive issues; other-session vs unchanged-rewrite overlap accepted as AC clarity.

## LESSONS LEARNED

### Technical

Blanket session cascade + ingest-then-embed lag is a latent semantic wipe: ingest deletes the index; a failed embed never restores it. Surgical invalidation is lag resilience, not just re-embed cost savings.

### Process

Nothing notable — plan sequence and file list held; `UNNEST(?::VARCHAR[])` for stale owner ids worked on first try.

### Million-dollar question

If surgical invalidation had been assumed from Phase 2, the writer would never have owned a session-wide embedding DELETE — invalidation would always have been compare-and-keep beside `first_seen_at` carry-forward. What we built is that foundational shape; no further redesign needed.

## PROCESS IMPROVEMENTS

None — Level 2 flow (plan → preflight → build → QA → reflect → archive) fit this enhancement cleanly.

## TECHNICAL IMPROVEMENTS

None required. Soft-stale search and content-hash columns remain out of scope / YAGNI for this contract.

## NEXT STEPS

- Close or annotate [issue #43](https://github.com/Texarkanine/stockroom/issues/43) as delivered.
- None otherwise — standalone L2 complete.
