# Active Context

## Current Task: Phase 2 · Milestone 2 — `sr-semantic` (`p2-embeddings-search`, sub-run m2)

**Phase:** `BUILD - COMPLETE` — all 6 plan steps built test-first; full gate green (lock-check clean, ruff check + format clean, REUSE compliant, **222 passed / 0 skipped** with torch present). QA runs next.

## What Was Done

Built `stockroom.semantic` strictly test-first, in plan order:

- **Step 1**: promoted `FakeEncoder` to `tests/conftest.py` (shared by `test_embed` + `test_semantic`); `test_embed.py` imports it (14 passed, no regression).
- **Step 2**: `embed_query` + `QUERY_PREFIX` (bge's asymmetric query instruction; threadable to `""`).
- **Step 3**: `SemanticHit` dataclass + `run_semantic_search` — index-accelerated cosine KNN over the `0003` HNSW index (`limit * OVERFETCH` chunk hits), Python **max-sim dedup** to one row per owner, owner-row join, read-only owns-connection path mirroring `query.run_query`.
- **Step 4**: `_format_hits` (similarity `score = 1 - distance`, single-line `PREVIEW_CHARS` display preview, `(N results)` trailer) + `main` (`-k/--limit`; empty-query/non-positive-limit/missing-warehouse guards all before the encoder is built — torch-free error paths).
- **Step 5**: one `importorskip("torch")`-gated real-model end-to-end (paraphrase ranks its message first) — **ran green locally** (torch present), CI-skipped.
- **Step 6**: docs — `techContext.md` (Semantic search section), `systemPatterns.md` (index-KNN → over-fetch → max-sim dedup + asymmetric query prefix pattern), `SKILL.md` (engine status).

## Files Created / Modified

- New: `skills/sr-search/src/stockroom/semantic.py`, `skills/sr-search/tests/test_semantic.py`.
- Modified: `skills/sr-search/tests/conftest.py` (shared `FakeEncoder`), `skills/sr-search/tests/test_embed.py` (import it), `skills/sr-search/SKILL.md`, `memory-bank/techContext.md`, `memory-bank/systemPatterns.md`.

## Key Build Decisions & Deviations

- **No schema/migration change** — purely additive engine + test code (the clean contrast with m1; no snapshot/head ripple).
- **`EMBED_DIM` in the cast** (`?::FLOAT[{EMBED_DIM}]`) rather than a literal `FLOAT[384]` — DRY with the schema width; also removed the otherwise-unused import.
- **Gate run with `--no-sync`, not `make ci`** — `make ci` depends on `make sync` (`uv sync --frozen`) which would strip the operator's out-of-band torch (torch-safe contract). Running the identical steps with `--no-sync` preserves torch and runs the suite *with* torch (the gated tests execute instead of skipping). `uv.lock` unchanged either way.
- `ruff format` reformatted the two new files (mechanical); `_format_hits` is a small dedicated renderer, deliberately not merged with `query._format_table` (preflight YAGNI advisory).

## Next Step

- QA review (invoke `niko-qa`) runs automatically.
