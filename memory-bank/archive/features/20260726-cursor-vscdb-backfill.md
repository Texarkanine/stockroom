---
task_id: cursor-vscdb-backfill
complexity_level: 3
date: 2026-07-26
status: completed
---

# TASK ARCHIVE: Cursor `state.vscdb` One-Shot Backfill

## SUMMARY

Shipped `stockroom backfill` — a harness-neutral, explicitly opt-in one-shot orchestrator with a source registry, whose first adapter (`cursor_vscdb`) excavates Cursor's legacy `state.vscdb` composer store into the warehouse. Conversations the nightly ingest never saw are now searchable alongside everything else: the operator's live run wrote **610 sessions / 64,002 messages / 50,740 tool calls in 28m53s** against a 5.7 GB store on a WSL→Windows mount.

This archive covers the whole arc recorded in `progress.md`, not just the feature build:

| Stream | Level | Outcome |
|---|---|---|
| `cursor-vscdb-backfill` — the feature (9 planned TDD steps) | 3 | Shipped; QA clean on all planned code |
| Build addenda ×3 — dry-run locking, model attribution, failed-call husks | — | Found by real-run + docs pass, all TDD'd |
| Side requests ×2 — dashboard `All` date range, Top Models clamp | — | Adjacent operator asks carried on the same branch |
| `cursor-vscdb-backfill-adhd-docs` — user-guide readability rework | 2 | Shipped |
| `cursor-vscdb-backfill-arch-docs` — architecture atlas rework | 2 | Shipped |
| `load-section-ia` — `ingest/` → `load/` section IA + 38-warning link debt | 2 | Shipped |
| `pr92-coderabbit-fixes` — nine judged PR #92 review items | 2 | Shipped |

Authoritative intent: [#84](https://github.com/Texarkanine/stockroom/issues/84). Delivered on [PR #92](https://github.com/Texarkanine/stockroom/pull/92), branch `cursor-backfill`.

## REQUIREMENTS

### Feature (Level 3)

**User story.** As a stockroom operator with years of history in a harness's legacy store, I want a one-shot backfill of that store into the warehouse so that conversations the nightly ingest never saw become searchable. Cursor's `state.vscdb` is the first such store; stockroom is cross-harness and others will follow.

1. Read Cursor `state.vscdb` **read-only** and emit warehouse sessions (with messages) for composers not already present.
2. **Deliberate deviation from #84:** nonzero bubble `tokenCount` is **not** a selection gate — backfill every missing composer, tokenless included.
3. Store allowlisted bubble `tokenCount` (`inputTokens` / `outputTokens`) at the grain the source reports it — on the message whose bubble carried it, only when nonzero — leaving session-grain `*_tokens` NULL for `session_token_usage` to roll up.
4. Carry clear provenance so backfilled rows are distinguishable from transcript/CLI-authored rows.
5. Expose the capability as an explicitly opt-in invocation, structured so a future harness's legacy store is an added adapter rather than a rewrite.
6. Document the finite nature of the corpus and that contemporary Cursor API tokens remain unavailable from vscdb.

**Constraints.** Not in nightly (core `ingest` unchanged; nothing schedules it). Existing warehouse rows win — never overwrite or prune transcript/CLI-authored sessions. Do not advance Cursor `_sync_state` watermarks. Fail-soft on unreadable/absent/locked stores; multi-GB DBs on slow mounts must stay practical. Do not map `composerData.tokenCount`, `tokenCountUpUntilHere`, or `contextUsagePercent` into warehouse `*_tokens` (context/UI meters — wrong semantics). TDD per `always-tdd.mdc`; production quality, not code golf.

**Acceptance criteria** — all met: legacy coverage created; re-run idempotent (no duplicates, no wiped transcript sessions, no orphan pruning); nightly behavior and watermarks provably unchanged; tokens honest at message grain with `token_grain = 'message'`; rows identifiable as vscdb-sourced; a second harness needs one adapter module, no orchestrator or CLI surgery; docs state run-once / finite corpus / API tokens still unavailable; full suite green.

### Rework 1 — ADHD user-guide readability (L2)

Ingest and backfill pages reordered for scan/action fit: command block first, mental-model prose demoted, Required Sequence as the lede with `stockroom embed` as step 4, "Why is This Even a Problem?" deleted, Why Quit / Why Ingest First collapsed to one sentence each, config-first on cursor-vscdb, `models` cell softened, Model Attribution + Token Counts folded under one Reference heading, plus link hygiene from the `ingest/backfill/` nest. Acceptance: an ADHD reader who reads only the first viewport of each page knows the next command to run.

### Rework 2 — Architecture atlas (L2)

`docs/architecture/backfill.md`: a named **Invariants** block under the lede (four load-bearing fences on screen before the essays); **Reuses The Writer** and **Grain And Honesty** compressed to roughly half length without loss of meaning; one sentence recording that a keep-predicate change under `--force` renumbers `message_id`s and invalidates embeddings. Diagram, Not On Any Automatic Path, Orchestrator Over Adapters, and mechanism depth explicitly not cut.

### Rework 3 — Load section IA (L2)

The operator had renamed `ingest/` → `load/` and split `schedule.md` out by hand, leaving `load/index.md` holding an orphaned **Harness-Specific Notes** block as its entire body and ~15 inbound links dangling. Requirements: `load/index.md` becomes a router (title, purpose, two catch-up commands, child map, no body); new `load/sources.md` takes the genuinely per-harness reference with the `#cursor-sessionsmodels-enrichment` slug surviving the move; `load/basic.md` absorbs the generic chunks; new `load/.pages` so `backfill` does not open the section alphabetically; **every** broken link in the tree repaired — Group A (19, the `ingest/`→`load/` rename) and Group B (19, the earlier `contributing/iteration.md` → `contributing/iteration/` nest), operator-confirmed as both in scope; strict build green at zero warnings from a red baseline of 38.

### Rework 4 — PR #92 CodeRabbit selected fixes (L2)

Nine operator-selected dispositions from review `#pullrequestreview-4782519076`, judged via `/pr-feedback-judge`; the rest stayed dismissed. Seven docs corrections (layout paths relative to `skills/sr-search/`; `secion` → `section`; API tokens unavailable from vscdb — closing original AC #7; "all instance" grammar; `--dry-run` prose no longer undercutting the quit-harness prerequisite; undo recipe wrapped in `BEGIN`/`COMMIT`; `progress.md` lede refreshed) and two `cursor_vscdb` stability fixes (`open_readonly` closes a failed ladder rung and percent-encodes the `file:` URI; `candidates` raises `BackfillError` instead of leaking `sqlite3.Error`).

## IMPLEMENTATION

### Creative Decisions (inlined — creative docs deleted at archive)

**OQ1 — bubble → message reconstruction. Selected: storable bubbles only.**

The input is `composerData:{id}.fullConversationHeadersOnly`, an ordered `[{bubbleId, type}, …]` list (present for 609 of 908 candidates; 26 older composers carry whole bubbles inline in a legacy `conversation[]` array; 273 have neither and are empty drafts). Options were one-bubble-one-message (A), storable-only (B), and merging tool bubbles into the preceding assistant turn to mimic the agent-transcripts shape (C).

B won. Dropping thinking-only bubbles loses nothing, because `thinking` is never persisted — under A those rows would be empty in every column (40,800 of 207,926 bubbles DB-wide). C's fidelity was an illusion: the source records no turn grouping (`grouping` is `null` on every sampled header), so the merge boundary would have been our invention, with genuinely ambiguous cases (a tool bubble opening a conversation) and destruction of the per-bubble `createdAt` / `tokenCount` alignment B preserves for free.

Implementation contract: keep a bubble when `text` is non-empty after strip **or** a tool call is present; `type == 1` → user, `2` → assistant, anything else skipped; text stored verbatim, `thinking` never read into it; at most one tool call per bubble (`tool_input` from `rawArgs`, falling back to `params`, then the raw string; `result` never stored); missing `bubbleId` rows skipped silently because Cursor prunes bubbles; `createdAt` parsed into naive UTC so `messages.ts` and real `started_at`/`ended_at` are populated — a grain the agent-transcripts parser cannot fill at all. Accepted tradeoff: vscdb sessions show tool calls as their own assistant messages, so their message counts run higher than a comparable transcript session.

**OQ2 — workspace identity. Selected: `cwd` from `workspace.json`, `project_id` from the native `workspaceId`, `workspace_key` derived by the writer.**

vscdb has no project-dir slug, so `paths.resolve_cwd`'s verify-don't-invert loop has nothing to verify against. `composerHeaders.workspaceId` exists for 532/908 candidates; `../workspaceStorage/{workspaceId}/workspace.json` resolves a real folder for 437/908. Options ranged from honest NULLs (A) through cwd-only (B) and a forward-encoded slug (C) to the native id (D).

D won because `workspace_key` already exists for exactly this problem — `systemPatterns.md` designates it the rollup key "so same-cwd sessions can cross-reference without mutating `project_id`". That dissolves the apparent conflict between honesty and cross-referenceability and makes C a solution to an already-solved problem. Confirmed live: Cursor `ide` and `cli` sessions sharing a project's `cwd` already share a `workspace_key` despite different `project_id` namespaces, and the warehouse already stores hash-shaped Cursor CLI `project_id`s — so D continues an existing pattern rather than minting an identity concept. Reading `workspace.json` is not filesystem guessing; it is an authoritative record at a path derived from the vscdb's own location. Accepted tradeoff: vscdb `project_id`s do not group with agent-transcripts slugs — deliberately, that is `workspace_key`'s job.

### Key Design Decisions

| ID | Decision |
|---|---|
| D1 | Read ladder `mode=ro` → `immutable=1`; copying the DB locally rejected as slower and less reliable |
| D2 | All key reads use index range bounds, never `LIKE` — `LIKE 'prefix%'` cannot use a SQLite index under the default case-insensitive setting, which is why the aborted `enhance-cursor-tokens` work was slow; range bounds are 60× faster on the mount |
| D3 | *(revised in plan review)* `backfill` is a **package with a source registry** and a documented four-name adapter contract, mirroring `ingest`'s orchestrator-plus-parsers shape; `cursor_vscdb` is simply the first adapter and the CLI grows `--source` |
| D4 | `entrypoint='ide'` with `source_path` = the vscdb path, for identifiability and one-line reversibility |
| D5 | Skip composers already in the warehouse and composers with no reconstructable messages |
| D6 | *(revised in plan review)* Tokens at **message grain** on the bubble that reported them; session `*_tokens` stay NULL and `session_token_usage` does the rollup |
| D7 | *(preflight)* `--force` re-parses only rows whose `source_path` is this adapter's own source |
| D8 | *(preflight, operator-decided)* `source_mtime` stays NULL; the writer gains a `utc_now()` fallback for `first_seen_at` |

D3 and D6 were both cargo-culted from the aborted `enhance-cursor-tokens` enrich design, where `sessions` was the only grain an enricher could reach. Operator plan review caught both. Migration `0007` already prohibited what D6 specified ("never invent session tokens from message sums"), and the Σ would additionally have made the view mislabel the grain as `'session'`.

### Files & Surfaces

Engine (`skills/sr-search/src/stockroom/`):

- **`backfill/__init__.py`** (278 lines) — orchestrator + source registry
- **`backfill/cursor_vscdb.py`** (542 lines) — the adapter: read ladder, candidate enumeration, bubble reconstruction, workspace resolution, model attribution
- **`backfill/__main__.py`** (138 lines) — CLI, per the convention both existing CLI-bearing packages follow
- **`__main__.py`** — `backfill` registered in the dispatcher's `SUBCOMMANDS`
- **`config.py`** — `[cursor].state_vscdb` key with `STOCKROOM_CURSOR_STATE_VSCDB` and `--state-vscdb`; the aborted task's negative ratchet `test_settings_has_no_state_vscdb_field` deleted as a visible diff line
- **`ingest/writer.py`** — the D8 one-liner: `utc_now()` fallback for `first_seen_at`
- **`dashboard/`** — side requests: `All` date-range preset, Top Models clamp to 10

Tests: `test_backfill.py` (731), `test_backfill_cursor_vscdb.py` (1,132), `test_backfill_cli.py` (207), plus additions to `conftest.py`, `test_config.py`, `test_ingest_writer.py`, `test_dispatcher_cli.py`, `test_dashboard_metrics.py`, and `tests-js/dashboard-core.test.mjs`.

Docs, in final post-IA shape: `docs/user-guide/load/{index,basic,schedule,sources,.pages}.md` and `load/backfill/{index,cursor-vscdb}.md`; `docs/architecture/backfill.md`; `docs/contributing/iteration/` (the old `iteration.md` split into six pages including `backfill-adapters.md`).

Branch total vs `main`: 59 non-memory-bank files, +4,309 / −442.

### Build Notes Worth Keeping

- **The import-edge guard matches `stockroom.backfill`, not the bare word `backfill`.** The bare word false-positived on the writer's own D8 docstring, which *explains* the backfill case. A guard that forbids naming the thing it protects against is a guard the next person weakens to write a sentence.
- **Workspace lookups are memoized in a per-run dict** threaded through the parse, not an `lru_cache` on the module function — a process-lifetime cache keyed on a path is stale state that leaks across tests.
- **The documented undo is not the one-liner the pre-mortem promised.** `stockroom query` opens read-only by design and the warehouse has no foreign keys, so reversing a run is three deletes through a DuckDB client (later wrapped in `BEGIN`/`COMMIT` by rework 4). Orphaned embeddings need no cleanup: `embed` already prunes vectors whose owner message is gone.

### The Three Post-Build Addenda

**Dry-run locking.** Writing the docs exposed that `--dry-run` took the single-writer lock and could silently create and migrate a warehouse. It now opens through `warehouse.open_current()` — read-only, never migrating — so rehearsing cannot queue behind a running ingest, and a missing or behind-head warehouse is a typed `BackfillError` naming the remedy. The lock test asserts **both** halves under one held flock (dry run completes, real run times out); asserting only the first would pass vacuously if the lock were never contended.

**Model attribution.** The operator's first real run left `sessions.models` at 0/610 and `messages.model` at 0/64,002 while `state.vscdb` carried both grains (`composerData.modelConfig.modelName` and a sparse per-bubble `modelInfo.modelName`). Fixed under TDD: `_model_name()` reads either grain, `_build_message` sets `model`, and `_parse_composer` unions the composer's selected model with every bubble's, deduped in conversation order. Verified read-only before recommending a re-run: 93/100 parsed composers carry session models, 12 multi-model, 246 messages with a per-message model. Two decisions: the literal `"default"` is stored as written (the ai-code-tracking sidecar already writes it for ordinary ingest — translating here would make one conversation report differently depending on which pipeline found it), and a **dropped** bubble's model still counts toward `sessions.models`, the deliberate opposite of the token rule (a token count is a property of one turn, so relocating it would lie about that turn's cost; a session-grain model list only claims the conversation used the model).

**Failed-call husks.** The operator spotted an unnamed slice holding 21% of Top Tools. Probing found 17,055 `tool_calls` rows with `tool_name = ''` — 15.5% of every tool call in the warehouse — all adapter-authored. Of 131,251 bubbles with `toolFormerData`, 18,058 (14%) have exactly one key: `additionalData: {"status": "error"}`. No name, no args, no `toolCallId`. These are husks a failed call leaves behind, not calls under a different field name. `_tool_call` now requires a non-blank name and declines otherwise; the existing keep predicate then drops husk bubbles carrying no text, which deliberately shrinks `messages` by 5,392 rows that had nothing in any column. Verified across 400 sampled composers: 20,612 named calls, **zero** blank.

### Side Requests (same branch)

**Dashboard `All` date range.** Added after `1y`, matching the sessions list. `All` is anchored to the data (`wrapped.totals.span.start`, already all-time and already fetched), not to the epoch — omitting bounds would mean each endpoint's *own* default window, and a literal epoch-to-now range would ask every chart for ~680 mostly-empty monthly buckets. `sessionsListHandoff()` translates an all-time metrics window into the list's own `All` when drilling in, because the two controls were never one component and their shared `default` id meant two different things.

**Top Models clamped to ten.** `metrics.models()` gained a keyword-only `limit: int = 10`, deliberately not URL-reachable (matching `projects` / `tools`). Bars clamp; the stacked area does not — measured first: the tail past rank 10 is 3.8% of attributed turns and 5.2% of conversations, and the area's height is already not a reconcilable total (45,206 attributed turns against 97,475 assistant messages). A ratchet test pins `model_trends` as unclamped so the asymmetry is not "tidied up" later. The clamp *is* the scrollbar fix with no CSS involved: `chartHeight` is `max(240, count × 34)`, so 21 models demanded a 714px canvas in a fixed panel.

### Rework Implementations

**ADHD docs.** Link baseline fixed first (30 → 0 strict warnings; ProperDocs requires explicit `…/index.md`, not directory trailing slashes), then the three page rewrites. A naive `user-guide/ingest/` → `user-guide/ingest/index.md` replace mangled `…/ingest/backfill/` into `…/ingest/index.mdbackfill/` — the origin of the longest-prefix-first rule. QA caught the CLI `--help` epilog still saying "do all three" without embed.

**Architecture atlas.** One focused file edit (Invariants block, two tightenings, keep-predicate fence) plus an anchor repair: the prior rework's heading demotion had broken `#cursor-sessionsmodels-enrichment`, which `installed-layout.md` consumes.

**Load section IA.** All seven steps in order, 38 warnings → zero. `load/index.md` became a 15-line router; `load/sources.md` ("Harness Sources", named to avoid colliding with backfill's legacy-store "source" one nav level away) took the per-harness reference; `basic.md` absorbed the generic chunks. `load/.pages` lists all five entries — with `validation.omitted_files: warn` under strict, a partial list would have failed the build the moment the file existed. Group A repaired across 12 files, Group B across 13, plus three references *outside* `docs_dir` (`skills/sr-initialize/SKILL.md`, `systemPatterns.md`, `techContext.md`). The four special-case retargets that were not pure path substitutions were applied individually **before** the mechanical bulk, longest prefix first — the direct countermeasure to the prior rework's mangling. One deliberate deviation: the enrichment heading shipped at `###` under `## Cursor` rather than the planned `##`, since the slug derives from heading text alone and a peer `##` would have reproduced the misplacement the rework existed to remove.

**PR #92 fixes.** Adapter TDD first (three red tests), then `open_readonly` URI encoding via `Path.resolve().as_uri()` (stdlib, and existing ladder substring assertions still hold) plus close-on-failed-rung, then `candidates` → `BackfillError`, then the seven docs corrections. The leak test needed a small connection proxy because `close` on `sqlite3.Connection` is read-only and cannot be monkeypatched.

## TESTING

TDD throughout, per `always-tdd.mdc`. All nine planned implementation steps ran as ordered cycles — stub tests → stub interface → write and fail for the right reason → implement → green — with no step's implementation begun before its tests failed. Every addendum and rework followed the same order (model attribution: seven tests, six failing first; husks: three tests, all failing first; dry-run lock: three tests; PR #92 adapter pair: three tests; dashboard `All`: four JS tests plus a static-markup assertion; Top Models clamp: three tests including the unclamped-`model_trends` ratchet).

**Preflight** (L3 feature) produced six findings, all remediated before build, and `.preflight-status` = PASS. It restructured the implementation steps into explicit ordered TDD substeps so the ordering could not be read past, moved CLI `main` to `backfill/__main__.py`, dropped `docs/advanced/cli.md` from scope, added D7, and — after the operator caught preflight's own first wrong answer — settled D8. Each rework ran its own preflight; the load-section IA preflight recorded five amendments (A1–A5), the substantive one being a stale `docs/contributing/iteration.md` path in `skills/sr-initialize/SKILL.md` that the strict build structurally cannot see because it lives outside `docs_dir`.

**QA** on the full branch (42 files, 4,606 insertions at the time) reviewed all seven constraints and found **seven findings, every one trivial, zero substantive** — no return to Build or Plan. Three integrity (two `writer.py` docstring artifacts from the D8 edit, a missing space in `tension:0.3`, and a `SourceSummary` docstring naming a field the dataclass does not have), one KISS (`modelTrends: ${windowLabel}` — a template literal wrapping one variable where all nine siblings assign it bare, confirmed not load-bearing before simplifying), one YAGNI (`BackfillSummary.written`, an aggregate property called by nothing), and two documentation (the user guide's `--force` section omitting the embed obligation the husk fix created, and `techContext.md`'s Engine Surfaces table — an exhaustive enumeration — omitting `stockroom.backfill`). QA deliberately left `systemPatterns.md` untouched and recorded that as a decision rather than an omission: nothing in it became false, and backfill's shape is a subsystem deep-dive that the file's own rules exclude. The divergent chart tensions (0.2 lines, 0.3 stacked area) were confirmed as operator visual tuning, not a defect.

Each rework's QA was also PASS with at most one trivial finding: the CLI `--help` four-step sync (ADHD), a paragraph split for scanability (architecture), two whitespace artifacts in a touched file (load IA), and a docstring expansion (PR #92).

**Gates, final run:** `make docs-build` strict exit 0 with zero warnings across 38 pages; pytest 784 passed / 2 skipped; 106 JS tests; ruff check + `format --check` clean; REUSE lint green; torch restored and `doctor smoke` confirming the 384-dim embed path.

**Live verification** carried more weight than any gate. The operator ran the documented sequence against the real 5.7 GB store and hand-verified the warehouse. Read-only probes against that store confirmed each fix before recommending a re-run. The dashboard `All` preset was verified against a throwaway 70-session warehouse spanning Mar 2025 – Jul 2026 under a `STOCKROOM_HOME` override on a second port, which was faster than waiting out a 25-minute backfill and is a repeatable way to exercise dashboard behavior against synthetic history.

## LESSONS LEARNED

**Probe the live store before trusting the adapter's view of it.** Both substantive post-build bugs — models at 0/610, 17k blank tool names — were invisible from warehouse-only or fixture-only inspection. Asking `state.vscdb` what keys it actually carries, rather than what the parser reads, is the check that caught them. The husk was invisible from the warehouse alone, where it just looked like a tool with no name.

**`message_id = '{session_id}#{ordinal}'` makes keep-predicate changes expensive and column fills cheap.** Model attribution changed no text and no ordinals, so all 64,002 message vectors survived `--force`. Declining husks dropped 5,392 messages, renumbered 31,782 downstream ones, and invalidated 13,178 of 87,691 embeddings (15%). Any future adapter change should ask which kind it is before recommending `--force`.

**A column whose meaning is defined against one source *shape* does not survive a change of shape.** `source_mtime` means "this conversation's source file was last written then" — true when ingest reads one file per conversation, meaningless when 2,039 composers share one store. It was silently doing two jobs (activity fallback via the dashboard's `COALESCE(started_at, source_mtime)`, and the seed for `messages.first_seen_at`), which only look like one field because every existing parser has a per-conversation file whose mtime answers both. Copying the *mechanism* (stat the source) instead of the *meaning* would have parked timeless composers on the run date.

**`or ""` against a `NOT NULL` column is how blank identities get stored.** `tool_name=str(tool_data.get("name") or "")` read as ordinary defensive coding and was the whole husk bug. Declining the row was always available; the schema made the lossy choice feel required. When identity is the point of a column (`tool_name`, `model`), absent means decline, not empty string.

**Closing the harness and ingesting first are not independent advice.** An immutable open cannot see the WAL tail, so quitting checkpoints it — which makes more recent composers visible, which widens the very ingest-overlap window that "ingest first" exists to close. Following one makes the other more necessary. They are also different *kinds* of rule: skipping ingest is a **cost** (a later ingest supersedes the reconstruction — wasted embedding work), while leaving the harness open is a **silent data gap** (conversations neither skipped nor counted nor reported, with the command exiting 0). That asymmetry is why the docs elevated both from advisory to REQUIRED ORDER.

**SQLite `file:` URIs treat an unencoded `?` in the path as the query delimiter.** The symptom is a successful open of the *wrong* database (`no such table`), not a connect error — silent misbehavior is worse than a hard failure, and the encoding test's first red caught exactly the operator-facing shape. Relatedly, CPython's `sqlite3.Connection.close` cannot be assigned, so observing cleanup in a test needs a proxy object.

**Docs lessons.** When rewriting relative links after a directory nest, apply special-case non-substitutions first, then bulk-replace longest prefix first — twice-validated now (the ADHD rework mangled paths; the IA rework avoided it by ordering). A link can be broken for two independent reasons at once, so warning *counts* are not cause counts; run an intermediate build after each group when renames overlap. Demoting a heading without checking slug consumers breaks `--strict` even when the demotion looks fine. And the strict docs build is a link checker for `docs/` **only** — prose outside `docs_dir` that cites a docs path is unguarded, which is exactly how the `sr-initialize` reference went stale unnoticed.

## PROCESS IMPROVEMENTS

**Enumerations that claim completeness are the recurring failure mode of this whole task.** The plan enumerated every `sessions` / `messages` column that mattered for structure, tokens, and identity — and never asked about `models` / `model`. Nothing in the build could have caught it: every test passed, because no test existed for a column no one had named. The same shape produced two of QA's three most substantive findings (`techContext.md`'s surface table and a docstring listing a dataclass's fields), both correct when written and made wrong by addition elsewhere. Prefer "see Y" indirection, or give exhaustive lists an explicit update step in the plan.

**Planned work and unplanned work had qualitatively different quality profiles.** Every QA finding lived in code written *after* the plan was validated — the post-build addenda and side requests, the work that had a real bug to chase and no preflight in front of it. The nine planned TDD steps came through clean. Test-first caught the behavior; nothing was watching the prose and the whitespace. When an addendum lands, a mini-preflight (or at least a doc/enumeration pass) pays for itself.

**A real run against production data is the only test that can catch unnamed columns.** Synthetic fixtures encode what the planner already knew — they never emitted `modelConfig`, never emitted husk `toolFormerData`, and never contended the writer lock the way a 25-minute run does. For a Level 3 task against an undocumented store, budget a dry-run-then-real-run *between* Build and QA, not only after.

**Decisions inherited from aborted work need explicit re-validation.** D3 and D6 both came from `enhance-cursor-tokens`, whose archive explained the *old* constraint clearly enough that carrying it forward felt like diligence. Operator plan review caught both. Flag "inherited from &lt;aborted task&gt;" decisions for deliberate re-derivation under the new mechanism.

**Prose is a verification surface, not just a deliverable.** Writing "dry-run does not open for writing" forced someone to check; it did. Both `--dry-run` errors — the false claim and then the realization that it need not take the lock at all — came out of a documentation pass. Conversely, elevating a step in the user-guide Required Sequence without updating the CLI `--help` epilog recreates the "docs and operator surfaces disagree" failure the original task already hit with `--force`→embed. Keep the epilog in the same edit.

**Judge review feedback before reworking it.** `/pr-feedback-judge` on the CodeRabbit review kept scope at nine selected fixes instead of the bot's full laundry list.

**Watch what a branch accumulates.** The two dashboard side requests rode along cleanly because they were dashboard-only and TDD'd, but they diluted QA's focus — every QA finding that was not a backfill docstring lived in that adjacent code.

**Docs-only work on a torch-provisioned machine should use `uv run --no-sync --no-config pytest`,** not `make test`, whose `uv sync` strips the per-machine torch install as a side effect. The Makefile documents this for `test-dashboard-py` but has no full-suite equivalent.

## TECHNICAL IMPROVEMENTS

- **A docs-path hygiene test.** A `test_skill_hygiene.py` case asserting that every `docs/...` path referenced from `skills/**` and `README.md` resolves on disk would close the `docs_dir` blind spot that let the `sr-initialize` path rot. Raised as a preflight advisory and declined at the time as out of scope; still worth doing.
- **A torch-safe full-suite Make target,** mirroring what `test-dashboard-py` already documents, so verification never has to choose between running the suite and keeping the environment.
- **`sessions.source_mtime` deserves a schema comment** recording that it is the dashboard's activity fallback and the `first_seen_at` seed, so the next parser author does not have to rediscover that it does two jobs.
- **The `load/` IA is the shape the section should have had from the start** — a router index, one page per concern, and `.pages` from day one. The junk-drawer index and the dual rename fallout were artifacts of incremental splits that never finished the IA; the same caution applies to the next section that grows past two pages.

## NEXT STEPS

None blocking. The feature is shipped, the operator's warehouse is backfilled and hand-verified, all four reworks are complete, and PR #92 carries the whole branch. The only outstanding item is the declined advisory above (the skill-path hygiene test), which is a future enhancement rather than a follow-up to this work.
