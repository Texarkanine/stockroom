# Stockroom Planning — Brainstorm

This directory is the **organized, well-formed capture of the founding brain dump** for `stockroom`, plus every scope decision made while refining it. It is the **single source of truth** that the real planning documents (Product Brief, Tech Brief, Roadmap) are written *from*.

These brainstorm files are **temporary**. Once the Product Brief, Tech Brief, and Roadmap are authored and verified, the brainstorm has served its purpose and can be retired.

## What Stockroom Is

Stockroom is a tool for ingesting your agentic-coding-harness conversations into a **local, queryable, faithful data warehouse** — so the *process, rationale, and context* of AI-assisted development (which git does not capture) becomes faithfully searchable, analyzable, and survivable across schema changes. The content it keeps is stored **in full** (no truncation at rest); truncation is a deliberate **read-time** feature. It draws inspiration from two prior tools (see `implementation-details.md`) but is a **clean-room, AGPLv3** product.

## How These Files Are Organized

The brain dump is split by which downstream document each idea feeds:

| File | Feeds | Contents |
|------|-------|----------|
| `product.md` | Product Brief (PB) | Audience, use cases, benefits, success criteria, constraints, non-goals |
| `tech.md` | Tech Brief (TB) | Stack, packaging, storage, ingest, embeddings, migrations, scheduling, distribution |
| `roadmap.md` | Roadmap | Rough phasing of the build |
| `implementation-details.md` | TB + build | Concrete reference facts: what to reuse, fix, and avoid; open technical questions |

## Decision Log

Every decision below is **settled** (confirmed by the operator) unless listed under "Open Items." IDs are stable so other documents can cite them.

| ID | Decision | Choice |
|----|----------|--------|
| D1 | Purpose | Ingest agentic-coding conversations into a local queryable warehouse (search, analyze, recap-later) |
| D2 | Harness scope | **v1 ingests BOTH Cursor and Claude Code** (O12 resolved). Schema designed against both to avoid single-harness bias; both plugin manifests ship |
| D3 | License | **AGPLv3** (already in repo) |
| D4 | Provenance / clean-room | Freely reuse/relicense the operator's own `cursor-warehouse` code; **strict clean-room vs `claude-warehouse`** (MIT) — no code, schema DDL, or unique ideas copied; only commonplace, generally-public concepts |
| D5 | Packaging | Ship a **uv *project*** (`pyproject.toml` + committed `uv.lock`) inside a skill directory; run via `uv run --frozen`. Pinned, hash-verified deps so nothing can be injected into a tool that reads all your conversations |
| D6 | Torch | **HARD requirement: do NOT lock torch across platforms with uv.** Lock everything else; torch stays platform-specific / out-of-band. Mechanism is a spike (possibly exclude torch from the locked set) |
| D7 | Storage | DuckDB single-file warehouse + VSS/HNSW vector index; **harness-neutral location** (`~/.stockroom/`, O1 resolved) |
| D8 | Embeddings | Local `sentence-transformers` (`all-MiniLM-L6-v2`, 384-dim); GPU when available, CPU fallback; **no external API** |
| D9 | Skills + namespace | `/sr-*`. v1: `sr-initialize`, `sr-search` (blended keyword+semantic entrypoint), `sr-query` (SQL), `sr-semantic` (pure vector), `sr-dashboard` |
| D10 | Dashboard | v1 headline UI. Launched on session-start via an **idempotent, fire-and-forget, bounded, non-erroring** hook, plus on-demand `sr-dashboard`. Not "always-running-while-coding" supervision |
| D11 | Recap | **Deferred to post-v1.** Reconceived as dashboard metrics dragged through time (time-series). Supersedes the earlier report/wrapped split |
| D12 | Migrations | Numbered, one-per-file SQL migrations inside the skill, git-tracked; a `schema_version` record; **lazy gate** inside each skill + the nightly job, applied under an exclusive lock; **preserve data, never force a full re-embed**; the session-start hook does NOT migrate |
| D13 | Concurrency | DuckDB single-writer; concurrent readers; serialize writes/migrations via lock; degrade gracefully when the DB is busy |
| D14 | Freshness | **Nightly scheduled ingest+embed is primary**, installed during onboarding; cron (Linux) / launchd (macOS); resolve correct absolute paths; WSL caveat noted |
| D15 | Distribution | `slobac`-style dual-manifest plugin + shared `skills/` tree + release-please versioning, published via the `txrk9-agent-plugins` marketplace; **both Cursor and Claude manifests ship** (O2 resolved) |
| D16 | Out of v1 | Token/cost estimation, AI-code attribution, source-file purge |
| D17 | Success | Personal-first, productization-grade, publishable on the operator's marketplace |
| D18 | Dev location | Build only in `/home/mobaxterm/git/stockroom` (fast, WSL-internal); never the slow `Documents` Windows mount |
| D19 | Faithful capture | **No truncation at rest** of kept content; truncation is a deliberate **read-time** feature (protect the context window). Ingest is **ETL, not mirroring** — no verbatim raw layer (O10 resolved → no); tool *outputs* not captured (inputs only) |
| D20 | Schema design & generality | Design empirically by enumerating each harness's actual fields (Cursor + Claude Code); capture a core field set (D22) + harness-specific artifacts (plan docs); preserve structural separation; ingest worst-case append-only blobs; stay harness-labeled and extensible |
| D21 | Conversation reconstruction | Every artifact (message, tool call, subagent, plan doc) links back to its conversation so a coherent thread can be reconstructed; linkage keys (conversation id, parent/child, ordering) are core, not an afterthought |
| D22 | Core captured fields | Timestamp; full message content; role/type; **model per conversation chain**; **subagent↔parent** linkage; tool calls (inputs only); agent thinking if the harness exposes it (optional); harness artifacts like plan documents |

## Open Items

Everything below is **resolved** except the torch spike (**O9**), which is genuinely empirical — it cannot be settled by writing a sentence, only by testing what `uv` actually does, and is the first task of the Tech Brief. IDs are stable so other documents can cite them.

### Resolved

| ID | Question | Resolution |
|----|----------|------------|
| O1 | Warehouse DB + config location (harness-neutral) | `~/.stockroom/` as the home; XDG-aware where the platform expects it (e.g. `~/.local/share/stockroom`, `~/.config/stockroom`) |
| O2 | v1 distribution: Cursor-only or dual manifests? | Both manifests ship (→ D15) |
| O3 | Ingest Cursor's `ai-code-tracking.db` for model enrichment? | Yes — only what's needed for model/labeling; attribution tables stay out (D16) |
| O4 | Migrations forward-only or reversible? | Forward-only |
| O5 | Keep `all-MiniLM-L6-v2` as the embedding model? | Yes |
| O6 | Dashboard server tech + offline assets? | Light/stdlib server with **vendored** front-end assets (no CDN); exact framework is a build-time pick |
| O7 | Ingest subagent transcripts? | Yes — linked to their parent (D21) |
| O8 | Windows-native scheduling for v1? | No — WSL/Linux cron + macOS launchd only; Windows-native is post-v1 |
| O10 | Keep a verbatim raw layer? | **No** — ingest is ETL into our schema, not a mirror (D19) |
| O11 | Isolate large message bodies into a dedicated content table? | No for v1 — inline storage; isolation is a possible later optimization |
| O12 | v1 *ingest* scope — Cursor only, or both? | **Both Cursor and Claude Code** (→ D2) |
| O13 | Output-truncation strategy? | Sensible per-skill defaults; `sr-search` reasons about the right level for the ask (D19) |
| O14 | Which harness artifacts to ingest? | Plan documents from both harnesses → a shared harness-labeled table, keyed to their conversation, when present (D20/D21) |
| O15 | Capture agent thinking/reasoning? | Capture when the harness exposes it and it's cheap; never a v1 blocker (D22) |

### Still Open

| ID | Question | Why it can't be decided now |
|----|----------|------------------------------|
| O9 | Torch packaging mechanism (the D6 "lock everything except torch") | Empirical. Needs a focused spike testing `uv` config (env markers / `required-environments` / optional groups / `explicit` index / torch-as-provided) on the target platforms while keeping `sentence-transformers` working. **First task of the Tech Brief; gates embedding work.** |

O9 does **not** block committing the brainstorm or authoring the Product Brief — it blocks *finishing* the Tech Brief. Resolving it by fiat would be fake completeness; it's a "go try it and see" investigation.

## Document Pipeline — What Happens Next

This is the authoritative "what must happen next," mirrored in `memory-bank/active/`.

1. **Brainstorm** (this directory) — *finalized and committed; the locked source of truth.* All scope decisions resolved except the torch spike (O9), which the Tech Brief executes.
2. **Product Brief** (`planning/product-brief.md`) — authored from `product.md`, modelled on Niko's `productContext` template but more verbose. *This is the hard, high-value work.* Verify before proceeding.
3. **Tech Brief** (`planning/tech-brief.md`) — authored from `tech.md` + `implementation-details.md` after the PB is solid; **executes the torch spike (O9)** and locks the schema by enumerating both harness formats. Verify.
4. **Roadmap** (`planning/roadmap.md`) — authored from `roadmap.md` after the TB is solid.
5. **Retire brainstorm**, and (when build begins) promote the design docs into the persistent memory bank (`productContext` / `systemPatterns` / `techContext`).

## Continuity

`memory-bank/active/` tracks this planning effort as its active task so the working context window can be closed and resumed at any step. Start there (`activeContext.md`) to pick up where we left off.
