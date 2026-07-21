# Progress

Ingest Cursor Agent CLI chats under `harness='cursor'`, pass through Claude native `entrypoint`, add `sessions.entrypoint`, and dedupe Cursor id collisions preferring `store.db` — warehouse/SQL only, no dashboard UI.

**Complexity:** Level 3

## 2026-07-21 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - Intent clarified and approved
    - Source/warehouse research completed (chats store.db, agent-transcripts, Claude entrypoint)
    - Complexity classified as Level 3
* Decisions made
    - No dashboard UI in this task
    - Linux roots only; no WSL/Windows multi-home discovery
    - Synthesize Cursor entrypoint from provenance (`cli` / `ide`); no system-prompt heuristics
    - On Cursor id collision, prefer chats `store.db` over agent-transcripts
* Insights
    - Claude desktop already writes the same JSONL shape with `entrypoint: claude-desktop`
    - Cursor has no native entrypoint field; path is sufficient for CLI certainty
