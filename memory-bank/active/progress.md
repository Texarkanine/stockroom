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
