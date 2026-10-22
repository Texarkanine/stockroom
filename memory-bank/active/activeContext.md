# Active Context

## Current Task: warehouse-file-growth
**Phase:** BUILD - FAIL (plan deficiency)

## What Was Done
- Added `test_schema_one_v1_file_migrates_to_head_and_keeps_storage_tag` (`tests/test_warehouse_open.py`) and `test_unscoped_semantic_plan_uses_hnsw` (`tests/test_semantic.py`)
- Added `scripts/shadow_duckdb_20.py` and `tests/test_shadow_duckdb_20.py`
- Rewrote the scoped-filter reason in `docs/architecture/embeddings.md` and `semantic.py`, and raised the scoped starvation fixture to 4,096 rows, because DuckDB 2.0.0 filters inside the HNSW scan
- The synthetic section passed on 2.0.0. The live run passed through branch A and failed at branch B

## Blocking Finding
- `pragma_hnsw_index_info` count is 280,901 against 133,793 rows on the healthy live copy, on 1.5.4 and 2.0.0. The extra entries are of unknown origin; compaction leaves them, a rebuild removes them. "Index count below row count" cannot mark a fold there. The fold itself reproduced: the replayed row is in the table and the index does not find it
- That count premise is in this plan's `classify`, in the doctor milestone's coverage check, and in the replay-bug invariant

## Next Step
- Operator decided (latest): drop the HNSW index; it is a two-way door. Exact search measured 130 ms on the live copy. This supersedes the fold-lookup decision and needs an L4 milestone re-plan: the index-stays invariant, the drop-and-recreate milestone, doctor's index checks, and the copy chain's index rebuild all change. Next: an L4 re-plan through `/niko-plan`
- The 2.0 lock is not landed; this checkout's engine stays on DuckDB 1.5.4
- Scratch copies from the run (about 85 GB, `baseline.duckdb` and the folded `warehouse.duckdb`) are in `/tmp/claude-1000/-home-mobaxterm-git-stockroom/99a0b37b-a8f2-4650-99f5-3edb42033c6b/scratchpad/shadow-live/`
