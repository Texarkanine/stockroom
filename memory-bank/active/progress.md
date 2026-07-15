# Progress

Implement surgical embedding invalidation on ingest session rewrite (compare-and-keep by message text) per https://github.com/Texarkanine/stockroom/issues/43 — stop cascade-deleting all session vectors when only append-only or unchanged history is rewritten.

**Complexity:** Level 2

## 2026-07-14 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - Intent clarified and approved against issue #43
    - Classified as Level 2: Simple Enhancement (self-contained change in ingest writer + tests; proposed solution already selected)
* Decisions made
    - Proceed with issue option B (text compare / compare-and-keep); no schema migration
* Insights
    - Failure mode is ingest eager cascade + embed lag, not embed itself wiping vectors

## 2026-07-14 - PLAN - COMPLETE

* Work completed
    - Mapped behaviors to `test_ingest_writer.py` contract tests (unchanged / append / text-change / remove / other-session / multi-chunk)
    - Planned compare-and-keep in `write_session` and removal of blanket embedding delete from `_delete_session`
    - Doc updates scoped to live system-model + architecture embeddings staleness wording
* Decisions made
    - Delete by explicit stale `owner_id` list (not join-against-messages-at-delete-time) so invalidation is independent of `_delete_session` order
    - No embed.py or schema changes
* Insights
    - Current cascade test asserts the *wrong* contract for #43; replace, don't merely soften

## 2026-07-14 - PREFLIGHT - COMPLETE

* Work completed
    - Validated TDD ordering (tests before writer impl), conventions (writer-only SQL), dependency impact (embed NOT EXISTS unchanged), completeness vs #43 ACs
    - Amended plan: pure `_embedding_owner_ids_to_invalidate` helper + unit cases
* Decisions made
    - Preflight PASS; advisory amendment applied within scope
* Insights
    - Blanket cascade is intentional today; conflict with old test/docs is the feature, not a blocker

## 2026-07-14 - BUILD - COMPLETE

* Work completed
    - Implemented `_embedding_owner_ids_to_invalidate` + surgical DELETE in `write_session`
    - Removed blanket embedding cascade from `_delete_session`
    - 7 new/replaced tests in `test_ingest_writer.py`; docs updated
    - Full suite: 530 passed, 3 skipped; lint/format clean
* Decisions made
    - Stale owners deleted by explicit id list (`UNNEST`) before session row delete
* Insights
    - Other-session isolation already held under old cascade; new value is retention on unchanged/append

## 2026-07-14 - QA - COMPLETE

* Work completed
    - Reviewed writer + tests + docs against plan (KISS/DRY/YAGNI/completeness/regression/integrity/documentation)
* Decisions made
    - PASS with no code fixes
* Insights
    - Overlap between other-session and unchanged-rewrite tests is acceptable AC clarity, not debris

## 2026-07-14 - REFLECT - COMPLETE

* Work completed
    - Wrote `reflection/reflection-surgical-embedding-invalidation.md`
    - Reconciled `systemPatterns.md` embeddings briefing with surgical invalidation
* Decisions made
    - Foundational shape is compare-and-keep beside first_seen carry-forward; no further redesign
* Insights
    - Cascade + embed lag is a semantic wipe failure mode, not merely wasted re-embed work
