---
task_id: cursor-cli-and-entrypoint-ingest
date: 2026-07-21
complexity_level: 3
---

# Reflection: cursor-cli-and-entrypoint-ingest

## Summary

Delivered Cursor Agent CLI `store.db` ingest under `harness='cursor'` with synthesized `entrypoint` (`cli`/`ide`), Claude native `entrypoint` passthrough, schema `0008`, and collision preference for chats over agent-transcripts — warehouse/SQL only, no dashboard UI. Build and QA both passed.

## Requirements vs Outcome

All acceptance criteria met: CLI chats as `cursor`+`cli`, IDE transcripts as `ide`, Claude passthrough, store.db wins on id collision, migration+writer cover the column, dashboard untouched. No descoping. One planned optional (`stockroom ingest --full` manual smoke) was skipped as non-blocking after full automated suite green.

## Plan Accuracy

Plan sequence (schema → model/writer → parsers → discovery → orchestrator → docs → verify) held. File list was accurate. Gaps filled during build: warehouse `_HEAD_VERSION` / migrate-runner / locked-snapshot pins needed bumping to 0008 (not called out as its own step), and the corpus `encode_for` roundtrip invariant had to exempt `entrypoint='cli'` because chats hash dirs are not encode slugs. Those were foreseeable once CLI `project_id` semantics were chosen; preflight/docs already noted hash `project_id`.

## Creative Phase Review

Ordered root-hash walk translated cleanly: `_root_blob_ids` + JSON leaf decode matched the fixture and real-sample shapes (string content, `tool-call`/`reasoning` parts). No alternate walk needed. Tradeoff (flat hash-list assumption) remains the right failure mode — tests fail loudly on layout drift.

## Build & QA Observations

Build was smooth under TDD; the only full-suite red was the head-version pin cluster. QA was clean (PASS) with two trivial nits (docstring whitespace, `createdAt` ms comment). Dual-root watermark + collision-set-from-all-discovered-chats were the load-bearing correctness details.

## Cross-Phase Analysis

Creative decision removed the biggest unknown before plan; preflight naming of orchestrator/golden tests paid off. The head-pin omission in the plan was the only build surprise — future schema tasks should list “bump `_HEAD_VERSION` / warehouse locked snapshot” as an explicit checklist item when adding a migration.

## Insights

### Technical
- Cursor CLI `project_id` (chats hash) breaks the IDE/Claude “cwd must re-encode to project_id” invariant; document and test that exemption explicitly rather than forcing encode_for onto CLI rows.
- Collision filters must use the full discovered chats id set, not only watermark-selected chats, or incremental runs can re-admit transcripts for already-ingested CLI sessions.

### Process
- When adding a numbered migration, treat head-version pin updates (`test_warehouse_open`, `test_warehouse_concurrency`, `test_migrate_runner`, locked snapshot import) as part of the schema step, not as leftover fallout from “full suite.”
