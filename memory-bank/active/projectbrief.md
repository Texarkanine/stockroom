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

## Rework

PR feedback on the shipped user-guide pages for ingest / backfill. Reorder and cut for ADHD scan/action fit; fix broken links from nesting backfill under `ingest/`. No engine or CLI behavior changes.

### Rework Requirements

1. **`docs/user-guide/ingest/index.md`:** First screen = one-sentence purpose + the incremental catch-up commands. Mental-model / ETL detail below. One-line link to backfill for legacy history. Demote or relocate the Cursor `sessions.models` enrichment block so it does not interrupt ingest → embed → schedule.
2. **`docs/user-guide/ingest/backfill/index.md`:** Open with what-it-is (one sentence) then the Required Sequence warning; make `stockroom embed` step 4. Delete "Why is This Even a Problem?". Collapse Why Quit / Why Ingest First to one sentence each. Running It leads with `stockroom backfill`, then dry-run / verbose.
3. **`docs/user-guide/ingest/backfill/cursor-vscdb.md`:** Pointing At The Store leads with config (recommended), then flag/env. How It Reads states the silent-miss consequence of leaving Cursor open (bold), with at most two short supporting sentences; uncommented architecture dump stays out. Soften `models` cell; fold Model Attribution + Token Counts under one Reference heading.
4. **Link hygiene:** Fix relative links broken by the `ingest/backfill/` nest on those pages; update `docs/architecture/backfill.md` and `docs/contributing/backfill-adapters.md` paths that still point at `user-guide/backfill/`.
5. **`make docs-build --strict` green.** No Python/test changes required unless a doc path is asserted somewhere.

### Rework Acceptance Criteria

1. An ADHD reader who only reads the first viewport of each of the three user-guide pages knows the next command to run.
2. Backfill Required Sequence includes quit → ingest → backfill → embed.
3. No HTML-commented TODO left in `cursor-vscdb.md` How It Reads.
4. Strict docs build passes; architecture/contributing links to the user-guide backfill pages resolve.

## Rework (architecture atlas)

PR feedback on `docs/architecture/backfill.md`: name the fences up front, cut design-diary voice in two paragraphs, and record the keep-predicate → `message_id` → embed invalidation trap. No engine or CLI changes. User-guide pages from the prior rework stay as shipped.

### Rework Requirements

1. **Invariants block:** Directly under the page lede, add a short named list of the four load-bearing fences (never on nightly; writer-only / no watermark; skip set + `--force` provenance; token grain + `source_mtime` NULL for a shared store).
2. **Tighten two paragraphs:** Compress **Reuses The Writer** (skip-set / ingest-first is cost not correctness) and **Grain And Honesty** (`source_mtime` NULL + `first_seen_at` run-clock fallback) to roughly half length; lead with what-is, then fence why. No loss of meaning.
3. **`--force` / keep-predicate fence:** One sentence under Never Clobbering: changing the keep predicate under `--force` renumbers `message_id`s and invalidates embeddings. Link or point to the user-guide recipe; do not paste the procedure.
4. **Do not cut:** diagram, Not On Any Automatic Path, Orchestrator Over Adapters, Reading Foreign Stores outbound pointer, or mechanism depth that the user-guide deliberately left on architecture.
5. **`make docs-build --strict` green.**

### Rework Acceptance Criteria

1. A changer who reads only the lede + Invariants block knows the four things they must not break.
2. The two target paragraphs are materially shorter and still state the same fences.
3. The keep-predicate / embed invalidation consequence is named on the architecture page.
4. Strict docs build passes; no user-guide regressions from this edit.
