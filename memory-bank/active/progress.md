# Progress

Diagnose why Cursor model fields go dark after ~2026-08-20, and — if Stockroom's ingest is the gap — patch it to read both the old and new Cursor formats.

**Complexity:** Level 2

## 2026-08-25 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - Classified as Level 2 from the approved brief
* Decisions made
    - Level 2: bug fix that is not a one-component typo (diagnosis may span transcript JSON, chats `lastUsedModel`, and the ai-code-tracking sidecar) and requires dual-format compatibility; no architectural change
* Insights
    - Live Cursor transcripts already document no native per-message model; session models are filled later (chats store and/or ai-code-tracking enrich)

## 2026-08-25 - PLAN - COMPLETE

* Work completed
    - Confirmed warehouse cliff: Cursor transcripts after 2026-08-20 have NULL `models` (4 filled on the 20th, then zero)
    - Confirmed live Windows tracking DB still has models through today; same schema Stockroom already reads
    - Isolated the abort: `Path("/mnt").iterdir()` / `is_dir()` raises `ENXIO` on `/mnt/i`, so the WSL walker returns `[]`
    - Wrote the Level 2 plan: fail-soft walk, unchanged SQL reader, `--full` once to backfill
* Decisions made
    - Not a Cursor format change — do not dual-read a new tracking schema
    - Discovery robustness is the patch; `read_enrichment` SQL stays
    - Already-ingested NULL rows are restored by `stockroom ingest --full`, not a new backfill surface
* Insights
    - `STOCKROOM_AI_TRACKING_DB` or an `ai_tracking_dbs` pin would have papered over this; the default walk must survive a single dead `/mnt/<letter>`
