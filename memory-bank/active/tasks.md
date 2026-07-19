# Task: Token Usage Grain & Rollups

* Task ID: token-usage-grain-rollups
* Complexity: Level 3
* Type: enhancement

Make token usage first-class with easy conversation rollups for Claude (message-grain today), without cornering the schema when a future harness reports session-grain only. Cursor attribution is out of scope.

## Open Questions

- [x] **Dual-grain token storage & rollup surface** → Resolved: nullable `sessions.*_tokens` + `session_token_usage` VIEW (`*_native`, `*_from_messages`, COALESCE effective); no fact table; no extra index (see `memory-bank/active/creative/creative-dual-grain-token-storage.md`)
