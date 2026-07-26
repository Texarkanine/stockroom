# Progress

Add an opt-in, one-shot backfill of legacy Cursor `state.vscdb` composers into the warehouse ([#84](https://github.com/Texarkanine/stockroom/issues/84)), selecting every composer missing from the warehouse rather than only nonzero-token ones, while leaving core nightly ingest and Cursor watermarks untouched.

**Complexity:** Level 3

## 2026-07-25 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - Loaded persistent memory bank; confirmed no in-flight task
    - Probed live `state.vscdb` to size the corpus: 934 backfill candidates (418 nonzero-token, 516 tokenless), 2025-03 → 2026-07, out of 2,065 composers total
    - Clarified and got operator approval on intent; wrote `projectbrief.md`
    - Classified the work as Level 3
* Decisions made
    - Nonzero bubble `tokenCount` is not a selection gate (deviation from #84 as written)
    - Ponytail intensity tempered: minimal but production-quality; no code golf
* Insights
    - The aborted `enhance-cursor-tokens` work (`memory-bank/archive/enhancements/20260722-cursor-token-counts-vscdb.md`) already established the harness facts this build depends on: `cursorDiskKV` over `ItemTable`, hybrid prefix/scan reads on slow mounts, and that contemporary bubbles carry `{0,0}` tokens
    - The operator's `~/.config/stockroom/config.toml` still contains a `[cursor].state_vscdb` key that current `stockroom.config` does not read — a leftover from the aborted branch, and a natural configuration hook to reconsider during planning

## 2026-07-25 - CREATIVE - COMPLETE

* Work completed
    - OQ1 explored as an algorithm question and resolved: `creative/creative-vscdb-message-reconstruction.md`
    - OQ2 explored as an architecture question and resolved: `creative/creative-vscdb-workspace-identity.md`
* Decisions made
    - Storable bubbles only (non-empty text or a tool call) become messages; thinking-only and empty bubbles are dropped; tool bubbles are not merged into the preceding assistant turn
    - `project_id` = native `composerHeaders.workspaceId`; `cwd` from `workspaceStorage/{id}/workspace.json`; `workspace_key` left to the writer's existing derivation
* Insights
    - Dropping thinking-only bubbles costs nothing: thinking is never persisted, so those rows would have been entirely empty (40,800 of 207,926 bubbles DB-wide)
    - `workspace_key` is the schema's designated cross-reference mechanism, which dissolves the apparent conflict between honest identity fields and project-scoped recall; confirmed live, where Cursor `ide` and `cli` sessions already share a key despite different `project_id` namespaces
    - vscdb bubbles carry per-message ISO timestamps, so backfilled sessions can populate `messages.ts` and real `started_at`/`ended_at` — a grain the agent-transcripts parser cannot fill at all

## 2026-07-25 - PLAN - COMPLETE

* Work completed
    - Full Level 3 plan written to `tasks.md`: component analysis, invariants, TDD test plan, 7-step implementation plan, technology validation, challenges, pre-mortem
    - Live technology validation against the 5.7 GB DB on the WSL→Windows mount
* Decisions made
    - Read ladder `mode=ro` → `immutable=1`; copying the DB locally is rejected as both slower and less reliable
    - All key reads use index range bounds rather than `LIKE`
    - Surface is a `stockroom backfill` subcommand in its own top-level module, so the nightly path keeps zero import edges to it
    - `entrypoint='ide'` with `source_path` as the vscdb path for identifiability and one-line reversibility
    - Skip composers already in the warehouse and composers with no reconstructable messages
* Insights
    - `LIKE 'prefix%'` cannot use a SQLite index under the default case-insensitive setting; the aborted `enhance-cursor-tokens` work was slow for exactly this reason, and range bounds make per-composer reads 60× faster on the mount
    - Composer ids share a namespace with agent-transcript session ids, which is why 1,131 already match — that makes "skip existing" exact, and means ordinary ingest would later supersede a backfilled row rather than duplicate it
    - The backfill roughly doubles the message corpus (~60k new against 43,892 today), so the embed backlog it creates is a documentation obligation

## 2026-07-25 - PLAN REVIEW - REVISED

* Work completed
    - Operator reviewed the plan and challenged D3 (Cursor-shaped surface) and D6 (session-grain tokens); both challenges held, and `tasks.md`, `projectbrief.md`, and the message-reconstruction creative were revised
    - Probed 120 composers / 14,446 bubbles on the live DB to settle the token-grain question empirically
* Decisions made
    - **D3 revised** — `backfill` becomes a package with a source registry and a documented four-name adapter contract, mirroring `ingest`'s orchestrator-plus-per-harness-parsers shape; `backfill.cursor_vscdb` is simply the first adapter, and the CLI grows `--source`
    - **D6 revised** — tokens are stored at message grain on the bubble that reported them; session `*_tokens` stay NULL and `session_token_usage` does the rollup
* Insights
    - The original D6 was inherited from the aborted `enhance-cursor-tokens` enrich design, where `sessions` was the only grain an enricher could reach. Carrying a decision forward across a change of mechanism silently carried its constraint too — worth watching for elsewhere in the plan
    - Migration `0007` already prohibits what D6 specified ("never invent \[session tokens\] from message sums"), and the Σ would additionally have made the view mislabel the grain as `'session'`
    - Every nonzero `tokenCount` in the sample sits on a bubble the OQ1 keep-predicate retains (0% on dropped bubbles), so the two creative decisions compose cleanly
    - Cursor's per-bubble counts are per-request usage with full prompt context in `inputTokens` — the same semantics as Claude's per-message usage, which is what makes message grain the *consistent* choice rather than merely the finer one
