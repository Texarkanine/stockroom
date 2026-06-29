# Active Context

**Current Task:** Phase 2 · Milestone 1 — Embedding pipeline (`p2-embeddings-search`, sub-run m1)

**Phase:** `BUILD - COMPLETE` — all 7 plan steps built test-first; `make ci` green (202 passed, 1 torch-gated skip); e2e smoke green. Proceeding to autonomous `/niko-qa`.

## What Was Done

Implemented the m1 embedding pipeline strictly test-first, in the planned dependency order, across three commits:

- **Steps 1-2** (`feat eecae4a`): `stockroom.embed` — pure-stdlib `chunk_text()` sliding window, the `Encoder` protocol, `embed_chunks()`, and `embed_pending()` (incremental current-model selection, per-chunk rows, messages-only). Torch-free via an injected `FakeEncoder` against `migrated_con`.
- **Steps 3-4** (`feat db88cc3`): `warehouse.ensure_vss()` (LOAD/INSTALL vss + per-connection HNSW persistence SET) wired into `open()` on every connection + the migrator; thin migration `0003` (cosine HNSW index, no INSTALL/LOAD in SQL); cumulative `0003_snapshot.json` (now with an `indexes` section). Migration-head ripple 2→3 across `test_migrate_runner`, `test_warehouse_open` (repointed to the 0003 snapshot), and `test_warehouse_concurrency`.
- **Steps 5-6** (`feat e3f6c96`): embedding cascade-delete in `ingest.writer._delete_session`; `BgeEncoder` (lazy torch, bge-small-en-v1.5, no `trust_remote_code`); the `python -m stockroom.embed [--full]` CLI with an `encoder_factory` injection seam.
- **Step 7** (docs, this commit): `techContext.md` (embeddings section + 0003/VSS note), `systemPatterns.md` (VSS-at-chokepoint + embed-second-writer patterns), `SKILL.md` (engine status updated).

## Files Created / Modified

- New: `src/stockroom/embed.py`, `src/stockroom/migrations/0003_embeddings_hnsw_index.sql`, `tests/test_embed.py`, `tests/test_schema_0003.py`, `tests/fixtures/schema/0003_snapshot.json`.
- Modified: `src/stockroom/warehouse.py` (`ensure_vss` + wiring), `src/stockroom/ingest/writer.py` (cascade), `tests/conftest.py` (`migrated_con` loads vss), `tests/test_migrate_runner.py`, `tests/test_warehouse_open.py`, `tests/test_warehouse_concurrency.py`, `tests/test_ingest_writer.py`, `memory-bank/{techContext,systemPatterns}.md`, `skills/sr-search/SKILL.md`.

## Key Build Decisions & Deviations

- **PK forces owner-replacement on (re)embed.** `embeddings` PK is `(harness, owner_table, owner_id, chunk_index)` — it excludes `embed_model`, so two models can't coexist at the same chunk. `embed_pending` deletes a selected owner's existing rows before inserting (corrected a test that wrongly expected coexistence). The same applies to `--full`.
- **Read-only `ensure_vss` advisory resolved.** Probed + tested: `LOAD vss` and `SET …persistence` both succeed on RO connections, so `ensure_vss` runs unconditionally on every `open()` (no writer-only scoping needed) — `test_open_reader_has_vss_loaded`.
- **0003 golden index section.** The cosine `metric` is not introspectable via `duckdb_indexes()` (and `expressions` is a VARCHAR `'[vector]'`, not a list), so the golden locks name/table/expressions and the metric is verified functionally by the KNN test.
- **Ripple under-enumeration (in-scope fix).** The plan listed `test_migrate_runner` + `test_warehouse_open`; `test_warehouse_concurrency` also carried two head-coupled assertions, updated in scope.
- **CLI testability seam.** `main(..., encoder_factory=BgeEncoder)` lets the CLI be tested torch-free with a `FakeEncoder`; the real-model `BgeEncoder` test is the lone `importorskip("torch")`-gated/CI-skipped surface.

## Integration Results

`make ci` green (sync, lock-check — **no `uv.lock` change**, lint, format-check, **202 passed / 1 skipped**, REUSE compliant). End-to-end smoke on real fixture roots: ingest 40 msgs → schema head 3 → embed 38 chunk vectors → cosine KNN nearest == queried message → incremental re-run = 0 → re-ingest cascaded to 0 → re-embed restored 38.

## Next Step

🐱 Autonomous **`/niko-qa`** (post-implementation semantic review). On QA PASS → `/niko-reflect`.
