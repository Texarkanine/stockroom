# Active Context

## Current Task: cursor-vscdb-backfill
**Phase:** BUILD - COMPLETE (all 9 steps; `make ci` + strict docs build green)

## What Was Done
- Probed this machine's live `state.vscdb` (5.7 GB, WSL→Windows mount) to ground the plan: 2,039 composers, 1,131 already in the warehouse, **908 backfill candidates** (609 with resolvable bubbles + 26 legacy-inline, 273 empty drafts), ~75,800 bubbles, 2025-03 → 2026-07.
- Component analysis: new `backfill` package (harness-neutral orchestrator/CLI + registry) with `backfill.cursor_vscdb` as its first adapter; writer, model, paths, warehouse all reused unchanged; the *absence* of an import edge from `ingest`/`schedule` is the "not nightly" guarantee and is asserted by tests.
- Resolved OQ1 (bubble → message reconstruction) via an algorithm creative: keep storable bubbles only; drop thinking-only/empty; tool calls stay on their own bubble-message rather than being merged into the preceding turn.
- Resolved OQ2 (workspace identity) via an architecture creative: `project_id` = native `workspaceId` (CLI-chats precedent), `cwd` from `workspaceStorage/*/workspace.json`, `workspace_key` left to the writer so vscdb sessions converge with same-`cwd` transcript sessions.
- Recorded six evidence-backed plan decisions, two of them measured live: the `mode=ro` → `immutable=1` open ladder (only `immutable=1` works on the mount), and index range bounds instead of `LIKE` (0.05 s vs 2.88 s per composer — this retires the "hybrid prefix/scan" pain from the aborted `enhance-cursor-tokens` work).
- Wrote the full TDD test plan (behaviors, infrastructure, integration, invariant guard tests), a 7-step implementation plan, technology validation, challenges, and a pre-mortem.
- **Operator plan review revised two decisions:**
  - **D3** — backfill is cross-harness by construction: a `backfill/` package with a source registry and a four-name adapter contract (`NAME`, `HARNESS`, `resolve_source`, `candidates`/`parse_all`), mirroring how `ingest` is an orchestrator plus per-harness parsers. A second harness's legacy store is a new file, not a refactor. CLI gains `--source`.
  - **D6** — tokens move from session-Σ to **message grain**. The Σ was cargo-culted from the aborted enrich design (which could only reach `sessions`); migration `0007` explicitly forbids inventing session tokens from message sums, and a fresh probe (120 composers / 14,446 bubbles) showed 100% of nonzero counts sit on bubbles OQ1 *keeps*, so per-message attribution loses nothing and lets `session_token_usage` roll up honestly as `token_grain='message'`.

## Operator Decisions On Record
- Tokens are **not** a selection gate — tokenless composers are backfilled too (deviation from #84 as written).
- Ponytail applies, but "don't over-cut": production-quality software, no cruft and no code golf.
- **No personal on-disk paths in committed artifacts.** Memory-bank docs, code comments, docs pages, and test fixtures use generic placeholders (`/home/u/p`, `<globalStorage>/state.vscdb`); real machine paths stay in the chat, never in the repo.

- **Preflight amended the plan in six places:**
  - Implementation steps restructured into explicit ordered TDD substeps (stub tests → stub interface → write and fail tests → implement); the old "— TDD cycle" label sat over implementation-only bullets.
  - `tests/test_config.py::test_settings_has_no_state_vscdb_field` — a live negative ratchet from the aborted `enhance-cursor-tokens` task — is now an explicit, justified deletion in step 1 rather than an unnamed "modify test_config.py".
  - CLI `main` moves to `backfill/__main__.py` (the convention `stockroom.ingest` and `stockroom.dashboard` both follow).
  - **D8 added (operator-decided)** — `source_mtime` stays NULL, and the writer seeds `messages.first_seen_at` from `utc_now()` when `source_mtime` is absent. The vscdb is one shared store, so its file mtime is not any composer's activity time; writing it would park timeless composers on the run date in the dashboard's `COALESCE(started_at, source_mtime)` window. Backfilled sessions plot historically off `started_at`/`ended_at`/`messages.ts` regardless.
  - `docs/advanced/cli.md` dropped from scope — its subcommand table is read-surfaces-only and omits `ingest`/`embed`.
  - **D7 added** — `--force` re-parses only rows whose `source_path` is this adapter's own source, so a parser fix does not require hand-written SQL while Constraint 2 still holds unconditionally.

## Build Outcome
- Shipped: `stockroom.backfill` package (orchestrator + registry, `cursor_vscdb` adapter, CLI), `[cursor].state_vscdb` config key, the D8 writer fallback, dispatcher registration, and four doc pages. ~1,500 lines across 14 files in two commits (`383e4ab` code, `b747eb9` docs).
- Every step ran as an ordered TDD cycle; the D8 change stayed the promised one-liner and left all three pre-existing `first_seen_at` cases untouched.
- Verification: `make ci` green (763 passed / 4 skipped, ruff clean, REUSE 323/323, lock fresh); `make docs-build` strict green; torch restored and `doctor smoke` confirms the embed path.
- Two build-time corrections worth carrying into QA: the ingest import-edge guard now matches `stockroom.backfill` rather than the bare word (the writer's own D8 docstring tripped it), and the pre-mortem's "one-line reversal" is actually three deletes through a DuckDB client, since `stockroom query` is read-only and the schema has no foreign keys. The docs say so.

## Next Step
- QA phase (`niko-qa` skill) — post-implementation semantic review. The build has not been exercised against the operator's real 5.7 GB `state.vscdb`; that is the obvious first QA move, starting with `--dry-run`.
