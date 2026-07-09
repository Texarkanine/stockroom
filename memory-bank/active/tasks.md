# Current Task: fix-cursor-model-enrichment

**Complexity:** Level 1

## Bug

Cursor model enrichment no-oped on real machines: wrong default DB path (`~/.cursor/ai-code-tracking.db`) and stale query against removed `conversation_model_usage`.

## Fix

- `default_db_path()`: env override → modern `~/.cursor/ai-tracking/...` → legacy flat path → WSL `/mnt/<drive>/Users/*/.cursor/...` candidates; first existing file wins.
- `read_enrichment()`: read `ai_code_hashes` (ordered) then optional `conversation_summaries`; graceful `{}` when absent/unknown.
- Synthetic fixture + enrich/fixture tests updated to the current schema; stale "DB absent on this machine" comments removed.

## Files

- `skills/sr-search/src/stockroom/ingest/enrich.py`
- `skills/sr-search/tests/conftest.py`
- `skills/sr-search/tests/test_ingest_enrich.py`
- `skills/sr-search/tests/test_ingest_fixtures.py`
- `skills/sr-search/tests/fixtures/transcripts/README.md`

## Verification

- Focused enrich/orchestrator tests: pass
- Full suite (`make test`): 417 passed, 3 skipped
- Live path resolution smoke: resolves `/mnt/s/Users/Austin/.cursor/ai-tracking/ai-code-tracking.db` with 117 conversations
- Operator owns: `stockroom ingest --full --harness cursor`

## QA

- **Result:** PASS
- Findings: techContext enrich blurb updated for current schema + candidate path search; no substantive defects
