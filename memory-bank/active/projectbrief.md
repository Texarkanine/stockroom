# Project Brief

## User Story

As a stockroom operator with years of Cursor history, I want a one-shot backfill of my legacy Cursor `state.vscdb` composers into the warehouse so that conversations Cursor never wrote to agent-transcripts or the CLI chats store become searchable alongside everything else.

## Use-Case(s)

### Use-Case 1: Excavate composer-only history

The operator runs the backfill once on a machine whose `state.vscdb` holds composers that normal ingest never saw. On the probing machine that is **934 composers spanning 2025-03 → 2026-07** (418 with nonzero bubble tokens, 516 without). Afterwards `sr-search` / `sr-query` / the dashboard cover that history.

### Use-Case 2: Safe re-run

The operator re-runs the backfill later (e.g. after more legacy composers age out of the live surfaces, or after an interrupted run). Nothing that normal ingest authored is damaged, and nothing is duplicated.

## Requirements

Authoritative intent: [#84](https://github.com/Texarkanine/stockroom/issues/84). This brief records the requirements as scoped for this session, including one deliberate deviation from the issue text.

1. Read Cursor `state.vscdb` **read-only** and emit warehouse sessions (with messages) for composers not already present.
2. **Deviation from #84:** nonzero bubble `tokenCount` is **not** a selection gate. Backfill every composer missing from the warehouse, tokenless included.
3. Set session-grain `*_tokens` only from the Σ of allowlisted bubble `tokenCount` (`inputTokens` / `outputTokens`) and only when nonzero; leave message-grain tokens NULL.
4. Carry clear provenance so backfilled rows are distinguishable from transcript/CLI-authored rows.
5. Expose the capability as an explicitly opt-in invocation that a human runs deliberately.
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
4. Backfilled sessions carry token sums only where bubbles actually reported nonzero values; everything else is honestly NULL.
5. Backfilled rows are identifiable as vscdb-sourced.
6. Docs state: run once (or rarely), corpus does not grow, contemporary Cursor API tokens still unavailable.
7. Full test suite green.
