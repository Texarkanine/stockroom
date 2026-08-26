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

## 2026-08-25 - PREFLIGHT - COMPLETE

* Work completed
    - Gemini 3.1 Pro preflight: PASS
    - `.preflight-status` written; Preflight checkbox marked
* Decisions made
    - No plan amendments
* Insights
    - Optional `mnt` on `_wsl_windows_candidate_paths` keeps existing `lambda: []` mocks valid (no args)

## 2026-08-25 - BUILD - COMPLETE

* Work completed
    - Added `_iter_dirs` and switched the WSL walker to per-entry fail-soft
    - Added five walker tests; enrich + orchestrator 47/47; full engine 821 passed / 4 skipped; dashboard JS 120 passed
    - Documented stale `/mnt/<letter>` skip in `docs/user-guide/load/sources.md`
    - Confirmed live discovery now merges the Windows tracking DB
* Decisions made
    - No SQL reader changes
    - Operator `--full` ingest left as a post-fix restore, not a new command
* Insights
    - Listing names first (`os.listdir`) is what makes a stale `/mnt/i` survivable; catching only the outer `iterdir()` is not enough

## 2026-08-25 - QA - COMPLETE

* Work completed
    - Fable semantic QA: PASS
    - Trivial docstring fix: "stated" → "statted" (matches `cache.py` wording)
    - `.qa-validation-status` written
* Decisions made
    - Residual unguarded `mnt.is_dir()` / `is_file()` TOCTOU left as pre-existing, not in this patch
* Insights
    - `_append_model` null/empty guard still has no direct test; unchanged by this build

## 2026-08-25 - REFLECT - COMPLETE

* Work completed
    - Wrote `memory-bank/active/reflection/reflection-cursor-model-ingest.md`
    - Reconciled persistent files: no edits
* Decisions made
    - Product/system/tech context still accurate; no briefing-altitude change
* Insights
    - List names, then stat: an `iterdir()` try/except does not survive a child `is_dir()` raise
    - Transcript ingest and model enrichment are different roots; only enrichment walks `/mnt`
