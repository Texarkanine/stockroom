# Progress

Rework on cursor-vscdb-backfill: ADHD reorder/cut of ingest + backfill user-guide pages and link hygiene after nesting under `ingest/backfill/`. Original feature work remains in the history below.

**Complexity:** Level 2

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

## 2026-07-25 - BUILD ADDENDUM (operator feedback) - COMPLETE

* Work completed
    - **Docs restructured on operator instruction**: backfill was inlined as sections of `ingest.md`, `lifecycle.md`, and `iteration.md`; it now owns `docs/user-guide/backfill/{index,cursor-vscdb}.md`, `docs/architecture/backfill.md`, and `docs/contributing/backfill-adapters.md`, with one-line pointers left behind. Nav wired through three `.pages` files. Title Case headings per operator preference
    - **The required operating sequence is now documented as required, not advisory**: quit the harness → `stockroom ingest` → `stockroom backfill`, with a "Why Quit The Harness" / "Why Ingest First" section explaining the silent cost of each omission, an admonition on the Cursor source page, and a `REQUIRED ORDER` epilog on `stockroom backfill --help`
    - **`--dry-run` no longer takes the single-writer lock** (TDD, three tests): it opens through `warehouse.open_current()` — read-only, never migrating — so rehearsing a backfill cannot delay or queue behind a running ingest
* Decisions made
    - A dry run against a missing or behind-head warehouse is now a typed `BackfillError` naming the remedy rather than a silently-created warehouse. Creating and migrating a database is not something a command called *dry run* should do, and `open_current` already had exactly that contract — no new open path was written
    - The dry-run lock test asserts **both** halves under one held flock: the dry run completes, and a real run times out. Asserting only the first would pass vacuously if the lock were never contended
* Insights
    - The two operator prerequisites are not the same kind of rule and the docs had to say so. Skipping `ingest` is a *cost* — the untouched watermark means a later ingest supersedes the reconstruction, so it is wasted embedding work and a corrupted summary, not lost history. Leaving the harness open is a *silent data gap* — an immutable open cannot see the WAL tail, so conversations are neither skipped nor counted nor reported, and a run-once command exits 0 having missed them
    - The two published recommendations interact in a way neither stated alone: "close Cursor for a clean read" *checkpoints the WAL*, which makes more recent composers visible, which widens the very ingest-overlap window that "ingest first" exists to close. Following one advice makes the other more necessary
    - Writing the docs is what caught both `--dry-run` errors — first the claim that it did not open for writing (it did), then the realization that it need not. Prose forced a precision the implementation had not been asked for; the QA finding and the fix both came out of a documentation pass

## 2026-07-25 - BUILD ADDENDUM (model attribution gap) - COMPLETE

* Work completed
    - **Operator ran the real backfill** (610 sessions, 64,002 messages, 50,740 tool_calls in 28m53s) and reported that the dashboard's model-usage-over-time chart did not extend back and that old sessions showed no model and no project
    - **Diagnosed against the live store**: `sessions.models` was 0/610 and `messages.model` 0/64,002, while `state.vscdb` carries both grains — `composerData.modelConfig.modelName` and a sparse per-bubble `modelInfo.modelName`
    - **Fixed under TDD** (seven tests, six failing first): `_model_name()` reads either grain; `_build_message` sets `model`; `_parse_composer` unions the composer's selected model with every bubble's, deduped in conversation order, into `sessions.models`
    - Verified against the real store read-only before recommending a re-run: 93/100 parsed composers now carry session models (12 multi-model), 246 messages carry a per-message model
    - Full suite green (775 passed, 2 skipped), ruff clean, `make docs-build --strict` green; adapter module docstring and `user-guide/backfill/cursor-vscdb.md` updated with a "Model Attribution" section
* Decisions made
    - The literal `"default"` is stored as written, not translated to NULL. It names the picker's setting rather than a model, but the ai-code-tracking sidecar already writes it for ordinary ingest — translating it here would make one conversation report differently depending on which pipeline found it
    - A **dropped** bubble's model still counts toward `sessions.models`, which is the deliberate opposite of the rule for token counts. A token count is a property of one turn, so relocating it would be a lie about that turn's cost; a session-grain model list only claims the conversation used the model, which stays true whether or not that turn left a storable row
* Insights
    - The gap was a *planning* omission, not an implementation slip. The plan enumerated every other column of `sessions` and `messages` and simply never asked about `models` / `model`. Nothing in the build could have caught it: every test passed, because no test existed for a column no one had named
    - The vscdb reports model attribution **better than nightly ingest can**. Ingest has no per-message model for Cursor at all, and gets session models only from the recent `ai-code-tracking` sidecar (272 of 1,260 ingest-authored Cursor sessions) — which is the real reason the chart started in May 2026. The backfill was blamed for a hole that predates it and now partially fills it
    - The re-run is far cheaper than the first run implies: `write_session` invalidates embeddings only for removed or text-changed message ids, and this fix changes no text, so all 64,002 message vectors survive `--force`

## 2026-07-26 - SIDE REQUEST (dashboard "All" date range) - COMPLETE

Adjacent operator request handled on this branch while the `--force` re-run was benchmarking out of band. Not part of `cursor-vscdb-backfill`; recorded here so the branch's contents stay accounted for.

* Work completed
    - Added an **`All` date-range preset** to the metrics view (after `1y`), matching the one the sessions list already had. TDD: four JS tests and one static-markup assertion, three failing first
    - `resolveWindowBounds` gained a `spanStart` parameter; `all` resolves to `[earliest recorded activity, now]`. New `sessionsListHandoff()` translates an all-time metrics window into the list's own `All` when drilling in
    - Verified live against a throwaway 70-session warehouse spanning Mar 2025 – Jul 2026 (`STOCKROOM_HOME` override, second dashboard on port 58077): all ten panels relabel to "All time", the model-usage chart renders 17 monthly buckets across the full span, and the drill-through opens the list with its `All` radio checked and no bounds in the URL
    - Gate: `make ci` green (773 passed, 4 skipped), 106 JS tests green, strict docs build green, torch restored after `ci`'s `uv sync`
* Decisions made
    - **`All` is anchored to the data, not to the epoch.** Omitting bounds could not express it — for metric endpoints that means each endpoint's *own* default window (30d, or trends' 14d/12w), which is also why `Default` is not the widest setting. A literal epoch-to-now range would have asked every chart for ~680 monthly buckets, nearly all empty
    - The anchor is read from `wrapped.totals.span.start`, which is already all-time by design and already fetched with every snapshot — no new endpoint, no backend change at all. An unanchorable or reversed `all` degrades to null rather than inventing a range
* Insights
    - The two date controls were never one component, and their shared `default` id meant two different things — "All" on the list, "let each panel choose" on the metrics view. Adding a real `all` id is what forced that latent ambiguity into the open; the handoff helper exists purely because the two vocabularies disagree
    - Verifying this needed a warehouse the writer lock was not holding. Standing up a scratch warehouse under `STOCKROOM_HOME` on a second port was faster than waiting out a 25-minute backfill, and is a repeatable way to exercise dashboard behavior against synthetic history

## 2026-07-26 - SIDE REQUEST (clamp Top Models to ten) - COMPLETE

Follow-on from the `All` preset: widening the range exposed that the two Top Models panels were the only ranked panels without a limit. Also not part of `cursor-vscdb-backfill`.

* Work completed
    - `metrics.models()` gained `limit: int = 10` (keyword-only), applied per grain through `_rank_model_counts`. Deliberately *not* reachable from the URL, matching `projects` / `tools`, which the endpoint dispatcher already calls as `endpoint(con, harnesses, since, until)`
    - TDD: three tests, all three failing first — per-grain clamp with aligned series widths, a caller-tunable `limit`, and a ratchet pinning `model_trends` as unclamped so the asymmetry is not "tidied up" later
    - Corrected `model_trends`'s docstring, which claimed its ranked order "matches `models()["by_message"]`" — now true only of the leading names
    - Gate: `make ci` green (776 passed, 4 skipped), 106 JS tests green, strict docs build green, torch restored after `ci`'s `uv sync`. Verified live on the real warehouse after `stockroom dashboard --replace`: both bar panels 10, trends 21, no scroll box
* Decisions made
    - **Bars clamp; the stacked area does not.** Measured first rather than guessed: the tail past rank 10 is 3.8% of attributed turns and 5.2% of conversations. An `<other>` band to keep the stack exact would have been an invisible sliver plus a legend entry plus a pseudo-label that is not a model
    - What decided it was that the area's height is already not a reconcilable total — 45,206 attributed turns against 97,475 assistant messages, because a turn only appears once its model is known. Preserving that height exactly buys less than it looks like. Operator chose to leave the series whole regardless, so the honesty question is moot either way
* Insights
    - The clamp *is* the scrollbar fix, with no CSS involved: `chartHeight` is `max(240, count × 34)`, so 21 models demanded a 714px canvas inside a fixed panel. Ten gives 340px and it fits
    - Palette stability came for free from the existing union order — `by_message` first, then `model_trends`. Because trends is unclamped and ranks identically, it now supplies the tail's hues that the clamped bars no longer name, and every colour assignment is byte-identical to before
    - Ranking a *time series* by a window-wide total can hide a model that dominated an era. It does not bite today (rank 11 is ~8% of its busiest month), but it is structural, and it is a second reason the area chart was the wrong place to clamp

## 2026-07-26 - BUILD ADDENDUM (failed-call husks) - COMPLETE

Operator spotted an unnamed slice holding 21% of Top Tools in the `All` window and suspected the backfill. Correct: 100% of it was adapter-authored.

* Work completed
    - **Diagnosed**: 17,055 `tool_calls` rows carried `tool_name = ''` — 15.5% of every tool call in the warehouse — across 227 sessions, all of them from `state.vscdb`
    - **Probed the store before assuming a missing key**: of 131,251 bubbles with `toolFormerData`, 18,058 (14%) have exactly one key, `additionalData: {"status": "error"}`. No name, no args, no `toolCallId`. These are husks a failed call leaves behind, not calls recorded under a different field name
    - **Fixed under TDD** (three tests, all failing first): `_tool_call` now requires a non-blank `name` and declines otherwise. `_build_message`'s existing keep predicate then drops husk bubbles that carry no text, with no change needed there
    - Verified read-only against the real store across 400 sampled composers: 20,612 named calls, **zero** blank, top names `read_file_v2` / `edit_file_v2` / `run_terminal_command_v2`
    - Gate: `make ci` green (779 passed, 4 skipped), strict docs build green, torch restored
* Decisions made
    - **The name is what makes it a call.** `tool_name` is the identity, and an unnamed call is unattributable to any tool — it can only pollute every ranking, which is exactly what it did. Blank-name calls are declined rather than stored, and `.strip()` guards the whitespace case even though the live store only produces the wholly-absent one
    - Declining the husk deliberately shrinks `messages` too: 5,392 of the husks were the *only* thing making their bubble storable. Those rows had no text, no model, and now no real call — empty in every column, which is precisely what the OQ1 keep predicate exists to exclude
* Insights
    - The `or ""` in `tool_name=str(tool_data.get("name") or "")` was the whole bug, and it read as ordinary defensive coding. `tool_calls.tool_name` is `NOT NULL`, so a blank string was the only way to write an unnamed call — the schema made the lossy choice feel like the required one, when declining the row was always available
    - **Re-running is not free, and the reason is `message_id`.** Ids are `'{session_id}#{ordinal}'`, so dropping 5,392 messages renumbers 31,782 downstream ones, changing their ids and invalidating **13,178 of 87,691** message embeddings (15%). The model-attribution fix cost nothing because it changed no text and no ordinals; this one shifts ordinals, so it does. Any future adapter change that alters the *keep predicate* carries this cost, while one that only fills columns does not
    - Two probes, one lesson: both this and the model gap were found by asking the store what it actually contains rather than trusting the adapter's view of it. The husk was invisible from the warehouse alone, where it just looked like a tool with no name

## 2026-07-26 - QA - COMPLETE

Post-implementation semantic review of the whole branch (42 files, 4,606 insertions vs `main`): the backfill deliverable, its three post-build addenda, and the two dashboard side requests carried alongside it. Operator hand-verified the feature out of band — the local warehouse is correctly backfilled.

* Work completed
    - Reviewed the changeset against the original plan on all seven QA constraints. **Seven findings, every one trivial, all fixed in QA; zero substantive findings**, so no return to Build or Plan
    - Integrity (3): two docstring artifacts in `writer.py` left by the D8 edit (a five-space run mid-sentence, a short-wrapped line), `tension:0.3` missing its space in `dashboard-core.mjs`, and a `SourceSummary` docstring that described "three skip counts" and named a `skipped` field the dataclass does not have
    - KISS (1): `modelTrends: ${windowLabel}` in `panelRangeLabels` was residue from deleting the ` · by message` suffix — a template literal wrapping one variable, where all nine siblings assign it bare. Confirmed not load-bearing (the `default` preset returns before that line) before simplifying
    - YAGNI (1): pruned `BackfillSummary.written`, an aggregate property called by nothing — the CLI prints per-source `SourceSummary.written`, and no test or doc referenced the roll-up
    - Documentation (2): the user guide's `--force` section omitted the embed obligation the husk fix created, and `techContext.md`'s Engine Surfaces table — an exhaustive enumeration — omitted `stockroom.backfill` despite it owning a registered dispatcher subcommand
    - Clean on the rest: no TODOs, stubs, unimplemented tests, debug artifacts, magic numbers, hardcoded shortcuts, or personal on-disk paths; DRY held (writer/model/paths/warehouse/timestamps all reused unchanged); no pattern regressions
    - Gates re-run after the fixes: ruff check + `format --check` clean (103 files), pytest 779 passed / 4 skipped, 106 JS tests, strict docs build green, REUSE 328/328, torch restored and `doctor smoke` confirming the 384-dim embed path
* Decisions made
    - **`systemPatterns.md` deliberately left untouched.** Nothing in it became false — the writer is still the only SQL touchpoint, `first_seen_at` is still not rebuildable from sources, and every consumer still reaches DuckDB through the chokepoint. Backfill's shape is a subsystem deep-dive, which that file's own rules exclude, and it already has `docs/architecture/backfill.md`. Recorded as a decision rather than an omission so a later reader does not "fix" it
    - The divergent chart tensions (0.2 for lines, 0.3 for the stacked area, from the terse `fix: curves` commit) are operator visual tuning, not a defect. Only the formatting slip was corrected; the values were left alone
* Insights
    - **Every finding lived in code written *after* the plan was validated.** The nine planned TDD steps came through QA clean; all seven findings trace to the post-build addenda and side requests — the work that had a real bug to chase and no preflight in front of it. Test-first caught the behavior; nothing was watching the prose and the whitespace
    - Two of the three most substantive findings were *enumerations that stopped being exhaustive*: `techContext.md`'s surface table and a docstring listing a dataclass's fields. Both were correct when written and became wrong by addition elsewhere, which is the failure mode of any document that claims completeness — the same shape as the model-attribution gap, where the plan enumerated every column of `sessions` but `models`
    - The `--force` doc gap is the cost of a fix's consequence being discovered after its docs were written. `progress.md` recorded "a `--force` re-run must be followed by `stockroom embed`" the day the husk fix landed, and the user guide never learned it — the memory bank knew something the shipped documentation did not

## 2026-07-26 - REFLECT - COMPLETE

* Work completed
    - Wrote `memory-bank/active/reflection/reflection-cursor-vscdb-backfill.md` — full Level 3 lifecycle review (requirements vs outcome, plan accuracy, creative hold-up, build/QA, cross-phase causal chains, technical and process insights)
    - Reconciled persistent files: no further edits. `techContext.md` already carries the `stockroom.backfill` engine-surfaces row from QA; `systemPatterns.md` and `productContext.md` unchanged (nothing factually wrong; backfill is subsystem deep-dive / feature accretion respectively)
* Decisions made
    - Persistent-file under-update preferred over ritual rewrite; the QA non-finding on `systemPatterns.md` stands
* Insights
    - The nine planned TDD steps and the three post-build addenda had qualitatively different quality profiles: planned work came through QA clean; every finding and both substantive gaps lived in unplanned work. That is the reflection's central process observation, not a new discovery at reflect time — see the reflection doc for the full set

## 2026-07-26 - REWORK INITIATED

* Trigger: PR feedback / operator review of user-guide ingest + backfill pages through an ADHD-readability lens (`/nk-chat` + `/i-have-adhd`).
* Feedback to address (docs-only; no product-code changes):
    1. `ingest/index.md` — put the catch-up command block first; demote mental-model prose; add a one-line door to backfill.
    2. `backfill/index.md` — Required Sequence is the lede (embed as step 4); delete "Why is This Even a Problem?"; collapse Why Quit / Why Ingest First to one sentence each; show plain `stockroom backfill` first in Running It.
    3. `cursor-vscdb.md` — recommend config first in Pointing At The Store; restore the ADHD-critical "close Cursor or you silently miss conversations" fact under How It Reads (mechanism stays thin; architecture owns the ladder).
    4. Soften the `models` table cell; collapse Model Attribution + Token Counts under one Reference heading.
    5. Fix path-nest fallout: relative links on the three pages (`../ingest.md` → `../index.md`, dashboard `../../…`); architecture/contributing pointers still naming `user-guide/backfill/` → `user-guide/ingest/backfill/`.
* Disposition: rework (not archive). Stale plan/context/status files cleared next; reflection + creative preserved.

## 2026-07-26 - COMPLEXITY-ANALYSIS (rework) - COMPLETE

* Work completed
    - Classified rework as Level 2 (simple enhancement): ADHD reorder/cut of three user-guide pages plus link hygiene from the `ingest/backfill/` nest; no product code
* Decisions made
    - Level 2, not Level 1: scope is deliberate readability restructuring across multiple pages, not a single typo/link fix
    - Architecture/contributing path updates included so the nest fallout does not leave dead links after the user-guide edit
* Insights
    - None beyond the chat review that triggered rework

## 2026-07-26 - PLAN (rework) - COMPLETE

* Work completed
    - Level 2 plan in `tasks.md`: link hygiene → ADHD rewrites of three user-guide pages → strict docs build; B1–B9 verification checklist
* Decisions made
    - Embed is step 4 of Required Sequence (not a later section)
    - Docs verification is `make docs-build --strict` + checklist; no pytest
    - Step 1 ripgreps all of `docs/` for stale paths, not only the brief's named files
* Insights
    - `ingest/index.md` sibling links (`quickstart.md` without `../`) were already broken by the directory nest — fixing them is part of making the ADHD flip real

## 2026-07-26 - PREFLIGHT (rework) - COMPLETE

* Work completed
    - Validated plan against live `docs/` tree; expanded Step 1 to every stale `ingest.md` / `backfill/` pointer (user-guide index/dashboard/search/skills/installed-layout, lifecycle, iteration, troubleshooting)
    - Encoded docs TDD order: fail strict build → fix → green baseline → ADHD rewrites
    - `.preflight-status` = PASS
* Decisions made
    - No re-level; advisory radical innovation (extra nav `.pages`) declined as out of ADHD-copy scope
* Insights
    - Nesting `ingest.md` → `ingest/index.md` broke a wide fan-out of relative links; the ADHD rewrite would have been verified against a red build if Step 1 stayed narrow

## 2026-07-26 - BUILD (rework) - COMPLETE

* Work completed
    - Fixed nest fallout across docs (30 → 0 strict warnings); ProperDocs requires explicit `…/index.md` not directory trailing slashes
    - ADHD rewrites of the three user-guide pages per B1–B8; Required Sequence is four steps including embed; deleted "Why is This Even a Problem?"
    - `make docs-build --strict` green after rewrites
* Decisions made
    - Config-first on cursor-vscdb; flag/env as one-off alternatives
    - Models cell softened ("may be empty"); Model/Token detail under `## Reference`
* Insights
    - A naive replace of `user-guide/ingest/` → `user-guide/ingest/index.md` mangled `…/ingest/backfill/` into `…/ingest/index.mdbackfill/` — order replacements longest-prefix first next time

## 2026-07-26 - QA (rework) - COMPLETE

* Work completed
    - Reviewed ADHD rewrites + link hygiene against rework brief; all requirements present
    - One trivial finding: CLI `--help` still said "do all three" without embed — synced to four steps and tightened `test_help_states_the_required_operating_sequence`
    - `.qa-validation-status` = PASS
* Decisions made
    - Help-text sync is documentation, not a behavior change; in scope for QA trivial fix despite "no CLI behavior" brief wording
* Insights
    - Elevating embed into the Required Sequence on the user guide without updating the CLI epilog recreates the old "memory bank knew, docs didn't" failure mode in reverse

## 2026-07-26 - REFLECT (rework) - COMPLETE

* Work completed
    - Wrote `reflection/reflection-cursor-vscdb-backfill-adhd-docs.md`
    - Persistent files reconciled: no edits
* Decisions made
    - Under-update preferred; path move does not invalidate tech/system/product altitude
* Insights
    - Longest-prefix-first when rewriting nested doc links; keep CLI epilog in the same edit as Required Sequence changes

## 2026-07-26 - REWORK INITIATED (architecture atlas)

* Trigger: PR feedback / `/nk-chat` review of `docs/architecture/backfill.md` through architecture-docs + ADHD lenses.
* Feedback to address (docs-only; no product-code changes):
    1. Add a short named **Invariants** block under the lede (four fences on screen before the essays).
    2. Tighten the two diary paragraphs in **Reuses The Writer** (skip-set / ingest-first cost) and **Grain And Honesty** (`source_mtime` / `first_seen_at`) — same meaning, half the prose; lead with *what*, then fence *why*.
    3. One sentence under **Never Clobbering** / `--force`: keep-predicate changes renumber `message_id`s and invalidate embeddings (husk-fix fence); user guide keeps the recipe.
* Leave alone: diagram, Not On Any Automatic Path, Orchestrator Over Adapters, Reading Foreign Stores outbound pointer, mechanism depth vs user-guide.
* Disposition: rework (not archive). Stale plan/context/status files cleared next; reflection + creative preserved.

## 2026-07-26 - COMPLEXITY-ANALYSIS (architecture rework) - COMPLETE

* Work completed
    - Classified architecture-atlas rework as Level 2 (simple enhancement): three surgical edits on `docs/architecture/backfill.md`; no product code
* Decisions made
    - Level 2, not Level 1: deliberate structure + fence naming, not a typo/link fix
    - Scope stays one page; user-guide pages from the prior rework are out of scope
* Insights
    - None beyond the chat review that triggered rework

## 2026-07-26 - PLAN (architecture rework) - COMPLETE

* Work completed
    - Level 2 plan in `tasks.md`: Invariants block → tighten two paragraphs → keep-predicate embed fence → strict docs build; B1–B5
* Decisions made
    - Invariants as punch list before essays, not a replacement for essays
    - Docs verification is `make docs-build --strict` + checklist; no pytest
* Insights
    - None

## 2026-07-26 - PREFLIGHT (architecture rework) - COMPLETE

* Work completed
    - Validated plan against live `docs/architecture/backfill.md` and user-guide `#fixing-a-run` anchor
    - Amended Step 1 for explicit docs TDD fail-first; pinned outbound force/embed link
    - `.preflight-status` = PASS
* Decisions made
    - No re-level; advisory radical innovation (mini change-surface table on the page) declined — overview already routes here
* Insights
    - User guide already owns the embed-after-force recipe; architecture only needs to name the trap

## 2026-07-26 - BUILD (architecture rework) - COMPLETE

* Work completed
    - `docs/architecture/backfill.md` rewritten per B1–B5 (Invariants + two tightenings + keep-predicate fence)
    - Fixed prior-rework anchor: `#### Cursor \`sessions.models\` Enrichment` heading restored the slug `#cursor-sessionsmodels-enrichment` for `installed-layout.md`
    - `make docs-build` strict green
* Decisions made
    - Anchor fix in scope under pre-mortem (“one-line path fix obvious”); not a user-guide ADHD rewrite
* Insights
    - Demoting a heading without checking slug consumers breaks strict builds even when the demotion itself looks fine

## 2026-07-26 - QA (architecture rework) - COMPLETE

* Work completed
    - Reviewed architecture page against rework brief + B1–B5; all requirements present
    - One trivial: split keep-predicate sentence onto its own paragraph for scanability
    - `.qa-validation-status` = PASS; `make docs-build` still green
* Decisions made
    - No substantive findings; diagram and structural sections left intact per B5
* Insights
    - None beyond the slug-consumer lesson from Build

## 2026-07-26 - REFLECT (architecture rework) - COMPLETE

* Work completed
    - Wrote `reflection/reflection-cursor-vscdb-backfill-arch-docs.md`
    - Persistent files reconciled: no edits
* Decisions made
    - Under-update preferred; atlas presentation does not change system/product/tech altitude
* Insights
    - Heading demotion must check slug consumers; Invariants-up-front is the atlas shape this page should have had initially

## 2026-07-26 - REWORK INITIATED (load section IA) - IN-PROGRESS

* Operator feedback (PR review + design chat)
    - `docs/user-guide/ingest/` renamed to `docs/user-guide/load/`; `schedule.md` split out; duplicate Scheduling section deleted from `basic.md` (uncommitted). Operator did this by hand before invoking rework.
    - `load/index.md` is now a section landing page whose entire body is the orphaned **Harness-Specific Notes** block — wrong content for a section index, and it is the first thing a reader sees.
    - Design review found the Harness-Specific Notes block is itself a junk drawer: four of its six chunks are generic ingest content, not harness-specific.
* Feedback to address (docs-only; no product-code changes)
    1. `load/index.md` becomes a router: title, one-sentence purpose, the two catch-up commands, child map. No body content.
    2. New `load/sources.md` takes the genuinely per-harness reference: default roots, `STOCKROOM_*_ROOT` overrides, Cursor chats best-effort parsing, Cursor `sessions.models` enrichment.
    3. `load/basic.md` absorbs the generic chunks: `ingest` / `--full` / `--verbose` block, `--harness` flag, `sr-initialize` first-full-load note.
    4. New `load/.pages` — none exists, so MkDocs sorts alphabetically and `backfill` lands first in the section.
    5. Repair the ~15 inbound links broken by the `ingest/` → `load/` rename across user-guide, architecture, and contributing; strict docs build is currently red.
* Decisions made
    - Rework, not archive. Reflection + creative docs preserved; plan/context/status files cleared.
    - Backfill stays under `load/` — design review rejected moving it to `advanced/` (hazard is a facet, not a hierarchy; `advanced/` is an escape-hatch tree).
* Insights
    - A section index with no children map invites orphaned content to settle in it.
    - The `#cursor-sessionsmodels-enrichment` anchor is consumed by `installed-layout.md`; the prior build phase already broke it once via heading demotion. Moving that block must preserve the slug.
