# Project Brief

## User Story

As a stockroom operator with years of history in a harness's legacy store, I want a one-shot backfill of that store into the warehouse so that conversations the nightly ingest never saw become searchable alongside everything else. Cursor's `state.vscdb` is the first such store; stockroom is cross-harness and others will follow.

## Use-Case(s)

### Use-Case 1: Excavate composer-only history

The operator runs the backfill once on a machine whose `state.vscdb` holds composers that normal ingest never saw — **~900 composers spanning 2025-03 → 2026-07** on the probing machine (pinned counts in `tasks.md`). Afterwards `sr-search` / `sr-query` / the dashboard cover that history.

### Use-Case 2: Safe re-run

The operator re-runs the backfill later (e.g. after more legacy composers age out of the live surfaces, or after an interrupted run). Nothing that normal ingest authored is damaged, and nothing is duplicated.

## Requirements

Authoritative intent: [#84](https://github.com/Texarkanine/stockroom/issues/84). This brief records the requirements as scoped for this session, including one deliberate deviation from the issue text.

1. Read Cursor `state.vscdb` **read-only** and emit warehouse sessions (with messages) for composers not already present.
2. **Deviation from #84:** nonzero bubble `tokenCount` is **not** a selection gate. Backfill every composer missing from the warehouse, tokenless included.
3. Store allowlisted bubble `tokenCount` (`inputTokens` / `outputTokens`) at the grain the source reports it — on the message whose bubble carried it, and only when nonzero — leaving session-grain `*_tokens` NULL for the `session_token_usage` view to roll up.
4. Carry clear provenance so backfilled rows are distinguishable from transcript/CLI-authored rows.
5. Expose the capability as an explicitly opt-in invocation that a human runs deliberately, structured so a future harness's legacy store is an added adapter rather than a rewrite.
6. Document the finite nature of the corpus and that contemporary Cursor API tokens remain unavailable from vscdb.

## Constraints

1. **Not in nightly.** Core `stockroom ingest` is unchanged; nothing schedules this. `sr-initialize` / cron must not acquire it.
2. **Existing warehouse rows win.** Never overwrite or prune sessions authored by transcript/CLI ingest.
3. **Do not advance** the normal Cursor `_sync_state` watermarks.
4. Fail-soft on unreadable / absent / locked `state.vscdb`; multi-GB DBs on slow mounts must remain practical.
5. Do not map `composerData.tokenCount`, `tokenCountUpUntilHere`, or `contextUsagePercent` into warehouse `*_tokens` (context/UI meters — wrong semantics).
6. TDD per `.cursor/rules/shared/always-tdd.mdc`; quality bar is production code, not code golf — lean, but no cut corners on correctness, validation, or docs.

## Acceptance Criteria

1. Running the backfill on a machine with legacy composers creates warehouse coverage for composer-only history that transcripts never ingested.
2. Re-running is idempotent: no duplicates, no wiped transcript-authored sessions, no orphan pruning.
3. Core nightly ingest behavior and Cursor watermarks are provably unchanged by the feature.
4. Backfilled messages carry tokens only where the source bubble actually reported nonzero values; everything else is honestly NULL, and `session_token_usage` reports `token_grain = 'message'` for them.
5. Backfilled rows are identifiable as vscdb-sourced.
6. Adding a second harness's legacy store means writing one adapter module against a documented contract — no orchestrator or CLI surgery.
7. Docs state: run once (or rarely), corpus does not grow, contemporary Cursor API tokens still unavailable.
8. Full test suite green.
