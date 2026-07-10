---
task_id: p2-embeddings-search
complexity_level: 4
date: 2026-07-07
status: completed
---

# TASK ARCHIVE: Phase 2 — Embeddings and Search

## SUMMARY

Phase 2 made the Phase-1 warehouse **findable by meaning**. It built the local embedding pipeline (`sentence-transformers` `bge-small-en-v1.5`, 384-dim, chunked, incremental, DuckDB VSS/HNSW cosine index), the pure-vector read surface (`stockroom.semantic`), a shared tested read-time truncation mechanism (`stockroom.truncate`, `--detail compact|snippet|full`), a shared presentation chokepoint (`stockroom.render`, `--format tsv|json|table`, tsv default), and the three `sr-*` wrapper skills: `sr-query` (safe LLM guidance for read-only SQL), `sr-semantic` (safe LLM guidance for vector search), and `sr-search` (the friendly-default judgement skill that routes a question to one or both siblings and synthesizes an answer).

Executed as a Level 4 project across seven sequential sub-runs (m1, m2, m3, m3.5, m4, m5, m6), each its own L2/L3 lifecycle closing green (`make ci`) and QA-clean before reflection. The project's defining event was a **mid-flight architectural realignment** after m1+m2: the originally planned Python keyword+semantic fusion module (`stockroom.search` with RRF blending) was recognized as the wrong layer for judgement and replaced by an LLM-judgement skill delegating to sibling wrapper skills — which reshaped the remaining milestones and pulled the wrapper skills forward from Phase 5.

## REQUIREMENTS

From the Phase 2 project brief ("Done When"):

- Semantic and blended search return relevant results over the real ingested history.
- New content re-embeds **incrementally** rather than from scratch.
- Read-time truncation is **demonstrably a feature** — full content preserved in the store, sensibly trimmed on output.

Cross-milestone invariants held throughout:

- **No truncation at rest** — embeddings derive from whole stored content via bounded chunks; truncation is read-time only.
- **Storage and embedding decoupled** — full text in the store; only bounded chunks reach the model.
- **Torch-safe contract (Phase 0)** — torch out of the lock, provisioned out of band, never an exact sync; `sentence-transformers` entered the lock via `make lock`.
- **Read surfaces open `read_only=True` through the `warehouse.open()` chokepoint** — DuckDB rejects writes; no app-level allow/deny-list.
- **Schema changes only via new forward-only numbered migrations** — one added this phase (`0003`, the HNSW index).
- **Harness-labeled and cross-harness by default**; **clean-room boundary** (no `cursor-warehouse` porting); **test-first + green `make ci`** for all Python, with prompt-skill behavior verified artisanally by the operator.

## MILESTONE LIST

The original decomposition (from the roadmap) was three milestones: embedding pipeline, `sr-semantic`, and a Python blended keyword+semantic `sr-search` entrypoint. Execution ran **seven** sub-runs after the mid-flight realignment:

1. [x] **Embedding pipeline** *(L3)* — VSS/HNSW index migration `0003` + chunk-and-encode embedder with incremental re-embed.
2. [x] **`sr-semantic` engine module** *(L2)* — `stockroom.semantic`: query embedding, cosine KNN, max-sim owner dedup, ranked read-only output.
3. [x] **Read-time output truncation** *(L2)* — shared tested `stockroom.truncate` (`--detail`, `…(+N)` elision marker) wired into both read surfaces.
3.5. [x] **Output format defaults** *(L2)* — shared `stockroom.render` chokepoint; `--format tsv` (default) / `json` / `table` on both surfaces. **Added during execution** (decision record: `planning/brainstorm/print-for-who.md`).
4. [x] **`sr-query` skill** *(L2)* — safe LLM wrapper SKILL.md over the read-only SQL surface. **Pulled forward from Phase 5** by the realignment.
5. [x] **`sr-semantic` skill** *(L2)* — safe LLM wrapper SKILL.md over the vector-search surface. **Pulled forward from Phase 5.**
6. [x] **`sr-search` skill** *(L3)* — the judgement skill routing to the siblings and synthesizing; replaced the original Python fusion milestone.

**Re-scope note:** after m1+m2, planning the original third milestone surfaced an architectural error (recorded in the search-surface architecture creative, inlined below). The prior m3 plan and its three creative docs (`creative-keyword-search-mechanism`, `creative-search-routing-and-fusion`, `creative-read-time-truncation`) were superseded and removed; the remaining work was re-decomposed into m3/m3.5/m4/m5/m6. Nothing shipped was reworked — realignment happened at its cheapest point.

## IMPLEMENTATION

All engine work lives in `skills/sr-search/src/stockroom/`; the wrapper skills live in `skills/sr-query/`, `skills/sr-semantic/`, `skills/sr-search/` (SKILL.md files, auto-discovered by both harness plugin manifests).

- **Embedding pipeline** (`embed.py`, `migrations/0003_embeddings_hnsw.sql`) — a torch-free-testable chunk-and-encode engine behind an injected `Encoder` protocol (`FakeEncoder` for CI; `BgeEncoder` for real work), writing one `FLOAT[384]` vector **per chunk** (not mean-pooled — a grounded improvement over the roadmap's sketch) through the chokepoint. Incremental selection via `NOT EXISTS` on owner rows plus session-grained cascade-delete in the ingest writer; `--full` flag for re-embed-everything. Model `bge-small-en-v1.5` chosen by a two-corpus empirical spike over the roadmap's `all-MiniLM-L6-v2` (same 384 dims, no migration). The HNSW cosine index ships as migration `0003` with experimental persistence enabled; `LOAD vss` + persistence SET live in the `warehouse.open()` chokepoint (`ensure_vss`), confirmed to work on read-only connections.
- **Semantic search** (`semantic.py`) — `python -m stockroom.semantic "<q>" [-k N]`: embeds the query with the bge query prefix (passages are stored prefix-free — the asymmetric-model contract), runs cosine KNN in the index-friendly `ORDER BY distance LIMIT n` form with over-fetch, dedups to one row per owner message by max similarity in Python (a `GROUP BY` would defeat the VSS acceleration), joins back to `messages`, and prints similarity-scored ranked output.
- **Read-time truncation** (`truncate.py`) — pure-function `truncate_cell` with detail levels `compact | snippet | full` and an informative elision marker reporting hidden volume (`…(+482)`), applied by both renderers. Full content always stays whole in `QueryResult.rows` / `SemanticHit.text` — the no-truncation-at-rest invariant is structural.
- **Output formats** (`render.py`) — shared presentation chokepoint exposing `format_query` / `format_semantic` over `tsv` (default; stream/pipe/LLM-friendly), `json` (`jq`-friendly), and `table` (human). `--detail` applies in every format. TSV needed zero escaping because `truncate_cell`'s whitespace collapse already removes tabs/newlines at every level. A `TYPE_CHECKING`-only import breaks the `render ↔ query/semantic` cycle.
- **`sr-query` skill** (`skills/sr-query/SKILL.md`) — routing guidance, the engine-invocation contract (`PYTHONPATH="$APP_DIR/src"` — see the m4 bug below), `--format`/`--detail` output discipline, context-blowout and wasted-tool-call guardrails, an introspection-first schema map, and live-verified worked examples including a `tool_input` JSON-extraction guardrail (`json_extract_string` over a `tool_name`-filtered subquery; naive `->>'key'` cast-errors on heterogeneous JSON).
- **`sr-semantic` skill** (`skills/sr-semantic/SKILL.md`) — query-phrasing advice (never hand-add the bge prefix), `-k`/`--format`/`--detail` discipline, guardrails (relevance-is-relative, re-phrase-don't-repeat, silent-staleness coverage check, full-text handoff to `sr-query`), torch-at-query-time notes including the stderr-noise observation.
- **`sr-search` skill** (`skills/sr-search/SKILL.md`) — the model-invocable judgement skill, 36 lines, the leanest of the three despite being the orchestrator: a routing table shipping the four verified desk-check cases as its own examples, delegation by sibling skill *name* with one relative-path fallback (`../sr-query/SKILL.md`, `../sr-semantic/SKILL.md`), six actionable synthesis lines, an empty-result fallback guardrail, and a one-line engine-home breadcrumb. **Zero invocation plumbing** — no `$APP_DIR`, `PYTHONPATH`, or uv flags anywhere in the file (grep-verified).

### Inlined creative decisions

**Search-surface architecture (project-level, decided mid-flight 2026-06-29).** Question: what *is* `sr-search` — a Python module that programmatically blends keyword + vector results, or an LLM-judgement skill orchestrating existing surfaces? Options: (1) Python fusion module (`ILIKE` keyword + semantic + RRF, always-blend) — the original plan; (2) `sr-search` skill shelling directly to the engine modules; (3) `sr-search` skill delegating to the sibling *skills*. **Chose Option 3.** Key insights: the Python router was dumb because judgement was in the wrong layer (the original plan had already rejected a Python auto-router as brittle and fallen back to always-blend); a Python keyword path is a worse `sr-query` (raw SQL already expresses `ILIKE`); and delegating to the skills rather than the modules keeps per-surface operational advice (truncation flags, guardrails, failure handling) in exactly one place. Tradeoff accepted: `sr-search` is not unit-testable (artisanal verification is the operator's chosen posture for prompt skills) and the wrapper skills had to be pulled forward from Phase 5. This decision graduated into a durable `systemPatterns.md` pattern during the m6 reflect: Python surfaces are power-user superpowers, `sr-*` skills are their safe wrappers, judgement is prose — no `stockroom.search` fusion module exists, deliberately.

**`sr-search` delegation mode (m6).** Question: how does prose in one skill "delegate" to another? Options: (A) delegate by sibling skill name with a relative-path fallback note; (B) explicit file-read with `$PLUGIN_ROOT`-resolved paths; (C) inline the sibling commands. **Chose A.** B reintroduces the path-resolution plumbing the litter audit flags, purely to find a file guaranteed to sit at a fixed relative location (committed layout = install layout, no build step); C is the architecture creative's rejected Option 2 wearing prose clothes. Consequence: `sr-search` needs **no invocation section at all**, mooting the litter audit's "m6 temporarily inherits the invocation litter" concession. Tradeoff accepted: `sr-search` cannot run self-contained — an agent must load a sibling first, which is the *point* of the architecture. Held with zero friction in build.

**`sr-search` synthesis grain (m6).** Question: what does `sr-search` produce — a fused ranked list, a narrated answer, or both? The both-surfaces case hands the agent two result sets with incomparable orderings (SQL rows carry no score; semantic similarity is relative within one query). **Chose Option C**: narrated answer citing its evidence by default; a single merged, *judgement-ordered* list when the ask is list-shaped; dedup across surfaces by `message_id`/`session_id` (a hit found by both routes is a strong-relevance signal, not a conflict); never blend or compare scores across surfaces. Key insight: a mechanical fused ranked list is the rejected RRF fusion module reborn as prose — the "wrong layer" finding applies to ranking, not just routing. Tradeoff accepted: no deterministic ranking for the both-surfaces case; determinism lives in the sibling surfaces.

**m1 sub-run creatives (summarized from the m1 reflection; the docs themselves were cleared at the m1→m2 boundary):** VSS provisioning as thin migration + chokepoint `ensure_vss` (held; read-only LOAD confirmed by probe + test); per-chunk storage grain justified by a measured long tail (max 202 KB message) and lossless storage; incremental re-embed via new-only selection + ingest cascade (zero schema change); owner grain messages-only; model selection by empirical spike. All five held in code with no rework.

## SYSTEM STATE

What exists now that didn't before Phase 2:

- **37,755+ embedding vectors** over the operator's real history, incrementally maintained: ingest cascade-deletes a re-ingested session's embeddings; `python -m stockroom.embed [--full]` re-embeds only what's missing.
- **Migration `0003`**: a persistent HNSW cosine index over `embeddings.vector`, with VSS loading and experimental persistence handled per-connection in the chokepoint.
- **Two complete read surfaces** — `python -m stockroom.query "<SQL>"` and `python -m stockroom.semantic "<q>" [-k N]` — both rendering through the shared `stockroom.render` chokepoint (`--format tsv|json|table`) with shared read-time truncation (`--detail compact|snippet|full`, informative elision markers), both opening `read_only=True`.
- **Three wrapper skills**, model-invocable in both harnesses with routing-bearing descriptions: `sr-query` and `sr-semantic` each own their surface's complete operational contract; `sr-search` owns routing judgement and synthesis and delegates operations by sibling name. End-to-end: a question enters `sr-search`, gets classified (exact/structured → `sr-query`; meaning-based → `sr-semantic`; ambiguous/broad → both; known-id → `sr-query`), the sibling contract drives the actual CLI calls, and the answer comes back narrated with id-deduplicated evidence.
- **Phase success criteria met**: semantic and blended search return relevant results over real ingested history (verified live in m2, m5, m6); re-embedding is incremental (m1); truncation is demonstrably a feature — tested Python, full content at rest, `--detail` selectable at read time (m3).

## TESTING

Test-first for all Python throughout; every sub-run gated on green `make ci` and a passing `/niko-qa` semantic review before reflection. Final suite: **266 passed, 2 torch-gated skips**; ruff lint+format clean; `uv.lock` locked; REUSE compliant.

- The injected-`Encoder` seam kept the entire pipeline (chunking, selection, per-chunk writes, incremental/`--full`, KNN dedup, rendering) testable with no torch in CI; the torch-gated `importorskip` end-to-end is the only test that can validate the asymmetric prefix contract in real embedding space, and it ran locally where torch was provisioned.
- Prompt skills were verified **artisanally per the project invariant**: every shipped example in all three SKILL.md files was executed live against the real (~380 MB) warehouse before being written in; m6 additionally ran three end-to-end passes (exact, meaning, both-surfaces) following the skill as written, with routing desk-checks shipped as the skill's own examples and a grep-verified no-invocation-token check.
- The `make ci` ⟂ torch tension (CI's `uv sync --frozen` strips out-of-band torch) recurred in m4/m5/m6 and was routinized: `make torch` restores, then a live smoke check.

## LESSONS LEARNED

- **Judgement belongs in the LLM layer; mechanics belong in Python.** The phase's central lesson, learned twice: a Python router can only be a brittle heuristic or a dumb always-blend (architecture creative), and a mechanically fused ranked list is the same mistake at the ranking layer (synthesis creative). Routing and synthesis shipped as prose; truncation, KNN, dedup, and rendering shipped as tested Python.
- **Re-read the PK columns of any table you're about to write derived data into, against your actual write pattern.** The `embeddings` PK excludes `embed_model`, which dictated replace-on-re-embed semantics — invisible to every Phase-2 design doc because they treated the Phase-1 schema as a given (m1's one genuine surprise).
- **"Copy the existing contract faithfully" is only safe if the existing contract is verified.** m4 discovered the engine-invocation incantation documented in three mutually-agreeing places was wrong in all three (`package = false` ⇒ bare `python -m` fails without `PYTHONPATH=<dir>/src`; pytest's `pythonpath` option had hidden the gap). Live verification of every example is what caught it.
- **Storage grain and read-time dedup are two halves of one design.** Per-chunk vectors (m1) forced the over-fetch-then-dedup KNN shape (m2) because a `GROUP BY` dedup defeats the VSS index; decide them together next time derived data is stored finer than it is read.
- **A deterministic fake proves mechanics, not geometry.** `FakeEncoder` verifies chunking/selection/dedup exactly, but the asymmetric model's prefix contract is a real-embedding-space property only the torch-gated end-to-end can validate.
- **Delegation-by-name between sibling skills needs no plumbing** when committed layout = install layout — a relative path is guaranteed in every install. Generalizes to any future cross-skill reference in this plugin.
- **The litter-test boundary for orchestrator skills**: criteria a skill needs to make its *own* decision (routing discriminators) are task knowledge even when they echo a sibling's topic; content the *delegated-to* skill needs is duplication. Will matter again for `sr-initialize` (Phase 4).

## PROCESS IMPROVEMENTS

- **For prose deliverables, front-loading design into autonomous creatives converts build into transcription.** m5 and m6 both had zero build rework; m6's two creatives plus the preflight amendment fully specified the content before authoring began.
- **Ship verification cases as the artifact's own examples.** The m6 preflight amendment (routing desk-check cases become the skill's shipped routing examples) generalizes m4/m5's "every shipped example is verified live" discipline: wherever content and test cases can be the same artifact, make them so — it removes a whole class of drift.
- **Realign mid-flight when the evidence says so.** The post-m2 re-decomposition (recorded in `milestones.md` itself) cost one planning session and saved building the wrong module; "nothing has shipped, so realignment is at its cheapest" was the correct trigger. The L4 milestone list absorbed the re-scope cleanly.
- **A grep-verifiable constraint is worth designing for.** The no-invocation-token check made "no operational duplication" auditable in one command — reuse it in the Phase-4 trimming pass across all three wrapper skills.
- **A quick cross-doc consistency pass after a multi-doc creative phase** would catch contradictions (m1's cascade-scope mismatch between two creative docs) at design time instead of at the line of code that must satisfy both.
- **Sibling-skill authoring against an established template collapses the cost of the second wrapper** (m5 after m4): iteration goes only into what is genuinely different about the surface.

## TECHNICAL IMPROVEMENTS

- **A shared launcher / on-path CLI for the engine** (Phase 4, `planning/brainstorm/stockroom-on-path-cli.md`): the run incantation is still copy-pasted prose in the two sibling skills and docs — exactly how it drifted into being wrong in N places at once (m4). The Phase-4 `sr-initialize` work is the designated consolidation point, including the litter-audit trimming pass.
- **Table-renderer consolidation**: `render.py` now holds the two relocated table formatters side-by-side; folding them into one `render_table(columns, rows, *, detail)` owning alignment + truncation is a single-file refactor, deliberately deferred until a third surface needs a table.
- **Clean torch-missing stderr on the semantic surface**: `BgeEncoder.__init__`'s lazy `import torch` fails as an unhandled traceback rather than the clean stderr form the other error paths use; a caught `ModuleNotFoundError` → "torch not provisioned; run make torch" (exit 1) would make the error table uniform. Candidate for whichever future milestone touches `semantic.main()`.
- **`duckdb_indexes()` is lossy for HNSW** (metric not introspectable; expressions a VARCHAR) — index metric contracts must be verified functionally (a KNN test whose ranking only holds under cosine).
- `test_packaging.py`'s `test_skeleton_skill_front_matter` name/docstring is cosmetically stale now that no skeleton skills ship — rename opportunistically when that file is next touched.

## CROSS-RUN INSIGHTS

- **The Million-Dollar Questions converged on chokepoints.** m2's answer (a shared retrieval helper) was correctly deferred by YAGNI; m3's and m3.5's answers (one `render_table` presentation chokepoint) were ~90% landed by m3.5 itself; m4's answer (a single canonical engine entrypoint) became the Phase-4 on-path-CLI plan; m5's answer (skills specify CLI contracts *first*, implementation matches) is an ordering insight for future surfaces. The recurring shape: every "if this had been foundational" answer is a single shared seam that the incremental milestones approached asymptotically — and the workflow correctly declined to build any of them speculatively.
- **Pre-paid risk made builds friction-light across the board.** m1's VSS spike, m2's predicted-and-dissolved unknowns, m3/m3.5's accurate challenge lists, and m4's live-verification discipline meant every sub-run's build phase executed its plan in order with no reordering — seven for seven. The pattern from Phase 1 (spike the load-bearing primitive) held: risk paid down in creative/preflight never resurfaced in build.
- **The one repo-wide bug of the phase was found by a skill, not a test.** The invocation-contract bug (m4) lived in documentation that pytest structurally could not exercise; the first non-test caller exposed it. Wrapper skills are integration tests for the operator-facing contract.
- **The litter audit arrived mid-project and improved the last deliverable most.** m4/m5 carry known Category A–C litter (scheduled for the Phase-4 trimming pass); m6, authored under the constraint, shipped at 36 lines with zero plumbing — evidence for authoring lean rather than trimming later.

## NEXT STEPS

- **Phase 3** per `planning/roadmap.md` — the memory bank is clean and the next phase can be initiated with `/niko`.
- **Phase 4 consolidations queued by this phase**: the on-path CLI / shared launcher (`planning/brainstorm/stockroom-on-path-cli.md`), the litter-audit trimming pass over `sr-query`/`sr-semantic` (`planning/brainstorm/skill-litter-audit.md`, reusing the m6 grep check), and the `sr-initialize` skill (where the routing-discriminator litter boundary will matter again).
- **Phase 5 retains** only empirical per-harness invocation-form verification for the skills (the wrapper authoring itself was pulled into this phase).
