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

## 2026-07-25 - PREFLIGHT - COMPLETE

* Work completed
    - Validated the plan against the live codebase: `config.py`, `ingest/{model,writer,paths,claude,cursor_chats}.py`, `__main__.py`, migrations `0004`/`0007`/`0008`, `schedule.render_payload`, `tests/{conftest,test_config,test_dispatcher_cli,test_shim_import_graph}.py`, REUSE config, and all five candidate doc pages
    - Six findings, all remediated in `tasks.md`; `.preflight-status` written as PASS
* Decisions made
    - Implementation steps restructured into explicit ordered TDD substeps (stub tests → stub interface → write and fail tests → implement) so the ordering cannot be read past
    - CLI `main` moves to `backfill/__main__.py` — the convention both existing CLI-bearing packages follow
    - `docs/advanced/cli.md` dropped from scope; the user-guide ingest page is the doc home
    - **D7 added** — `--force` re-parses only rows whose `source_path` is this adapter's own source
    - **D8 added (operator-decided)** — `source_mtime` stays NULL and the writer gains a `utc_now()` fallback for `first_seen_at`; preflight's first answer (use the vscdb file mtime) was wrong and the operator caught it
* Insights
    - The aborted `enhance-cursor-tokens` task left a live negative ratchet, `test_settings_has_no_state_vscdb_field`, that fails the moment step 1 lands. A plan that says "modify `test_config.py`" is not the same as a plan that says which assertion is being reversed and why — and an abort-era guard is exactly the kind of thing a later task reverses legitimately
    - D5's skip set protects the warehouse from backfill but also protects bad backfill output from correction. The asymmetry only became visible after D4 made backfill-authored rows exactly identifiable — the provenance decision paid for the escape hatch
    - `sessions.source_mtime` is not inert provenance: the dashboard's activity clock is `COALESCE(started_at, source_mtime)`, so what goes in it decides where a session lands on the timeline
    - A column whose meaning is defined against one source *shape* does not survive a change of shape. `source_mtime` means "this conversation's source file was last written then" — true when ingest reads one file per conversation, meaningless when 2,039 composers share one 5.7 GB store. The first preflight answer copied the mechanism (stat the source) instead of the meaning (when was this conversation last active), and would have parked timeless composers on the run date
    - `source_mtime` was silently doing two jobs — activity fallback *and* the seed for `messages.first_seen_at`. They only look like one field because every existing parser has a per-conversation file whose mtime happens to answer both. The backfill is the first source where they diverge, which is what exposed the latent gap: any parser omitting `source_mtime` was permanently discarding observation time

## 2026-07-25 - BUILD - COMPLETE

* Work completed
    - All nine implementation steps executed as ordered TDD cycles (stub tests → stub interface → write and fail → implement → green), in the plan's order, with no step's implementation begun before its tests failed for the right reason
    - New `stockroom.backfill` package: orchestrator + source registry (`__init__.py`), the `cursor_vscdb` adapter, and the CLI (`__main__.py`); `backfill` registered in the dispatcher's `SUBCOMMANDS`
    - `[cursor].state_vscdb` config key added (with `STOCKROOM_CURSOR_STATE_VSCDB` and `--state-vscdb`); the aborted task's negative ratchet `test_settings_has_no_state_vscdb_field` deleted as a visible diff line
    - D8 landed as the promised one-line writer change; all three pre-existing `first_seen_at` cases passed unmodified, so the inertness claim held
    - Docs written per plan: user guide backfill section, `installed-layout` config row, lifecycle "not on any schedule" section, contributor adapter contract; `docs/advanced/cli.md` correctly left alone
    - Verification: `make ci` green (763 passed, 4 skipped; ruff check + format-check clean; REUSE 323/323; lock fresh), `make docs-build` strict green, torch restored via `stockroom shim ensure-env` and confirmed with `doctor smoke`
* Decisions made
    - The `ingest`-has-no-`backfill`-import-edge guard matches on `stockroom.backfill`, not the bare word `backfill`. The bare word false-positived on the writer's own D8 docstring, which *explains* the backfill case — a guard that forbids naming the thing it protects against is a guard that gets weakened by the next person who needs to write a sentence
    - Workspace lookups are memoized in a per-run dict threaded through the parse rather than an `lru_cache` on the module function; a process-lifetime cache keyed on a path is stale state that leaks across tests
* Insights
    - The documented undo is not the one-liner the pre-mortem promised. `stockroom query` opens read-only by design, and the warehouse has no foreign keys, so reversing a run is three deletes through a DuckDB client, not one through the shipped CLI. Worth noticing that a reversibility claim made during planning went unexercised until the docs step forced someone to actually write the command
    - Orphaned embeddings need no manual cleanup: `embed` already prunes vectors whose owner message is gone, so the undo path ends at the three table deletes
    - `--force`'s safety is entirely a consequence of D4. The flag is one predicate (`source_path = <this adapter's source>`) precisely because provenance was decided earlier; had `source_path` been anything less exact, the escape hatch would have needed its own bookkeeping column
