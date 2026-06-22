# Brainstorm — Tech

Raw material for the **Tech Brief**. Captures the intended stack and the load-bearing technical decisions. Concrete reference facts (what to reuse/fix/avoid from prior tools) live in `implementation-details.md`.

## Language and Runtime

Python, managed with [uv](https://docs.astral.sh/uv/), following the operator's `cursor-warehouse` experience.

The defining decision: stockroom ships as a **uv *project*** — a real `pyproject.toml` with a **committed `uv.lock`** — that lives **inside one of the skill directories** and is executed with `uv run --frozen` (or `uv sync --frozen`). This is the headline trust property.

### Why a Locked Project, Not Loose Scripts

The reference tools run single-file scripts via `uv run --script` with **loose PEP 723 ranges and no lockfile**, so dependencies are re-resolved fresh on essentially every run. For a tool that reads *every one of your conversations*, that is an unacceptable dependency-injection surface.

Research confirms the fix and the nuance:

- `uvx` / `uv tool run` is for ephemeral published tools and does not honor a project lockfile.
- A committed lockfile + `--frozen`/`--locked` *does* pin exact versions, and uv lockfiles record **hashes** by design, so the secure path is also the reproducible path.
- Two viable shapes exist: **project mode** (`pyproject.toml` + `uv.lock`, what we're doing) or **script mode** (`script.py.lock` next to each script). We choose project mode for a real, shippable, locked application.

## The Torch Exception

**Hard requirement: never attempt to lock torch across all platforms with uv.** That is a known fool's errand (CPU vs CUDA vs Apple MPS wheels), and we will not do it absent a genuine breakthrough.

The goal is therefore: **lock everything *except* torch**, and let torch be resolved/installed in a platform-specific, out-of-band way. The open spike (O9) is *how*:

- Can torch be excluded from the locked resolution while `sentence-transformers` still depends on it (e.g., uv environment markers, `required-environments`, optional groups, an explicit/`explicit = true` index, or treating torch as provided)?
- The operator's existing approach is a **user-level `~/.config/uv/uv.toml` extra index** pointing at `https://download.pytorch.org/whl/<accel>` for the GPU wheels, with macOS/CPU falling back to defaults — that works but sits *outside* any shipped lockfile, which is acceptable precisely because torch is the explicit exception.
- A `uv_torch_smoke`-style verification (print version + `cuda.is_available()`) should confirm a working install during onboarding.

This tension (a fully-locked app vs platform-specific torch) is resolved by **declaring torch the one documented thing outside the lock**, and is the single most important item to nail down in the Tech Brief.

## Faithful Capture (Core Principle)

Faithful recall is the whole point — it is what separates stockroom from a "fun toy" that can only report *how much* AI you used. The references truncate the content they keep, which repeatedly forced the operator back to the original transcripts.

**Two distinct ideas, often conflated:**

- **No truncation at rest.** The fields stockroom chooses to keep are stored *in full*. Never a 2000-char stub.
- **Smart truncation at read.** Skills truncate *output* deliberately, so querying a 200 KB field doesn't blast the agent's context window. The `sr-search` entrypoint should reason about an appropriate output-truncation level for what the user asked (O13). This is a feature — the opposite of the references' destructive at-rest truncation.

Measured on the operator's live `cursor-warehouse` (2026-06-22; queries in `implementation-details.md`): `text_content` and `user_query` are hard-capped at **2000 chars** and `tool_input` at **500** — about **17%** of messages exceeded the 2000 cap. Against the source JSONL, true sizes are median ~0.5 KB, p99 ~14 KB, max single field ~**200 KB**, nothing over 1 MB.

DuckDB makes untruncated storage trivial: `VARCHAR` has no length limit (4 GB ceiling, UTF-8) and database files scale to terabytes; the only real cost is *operating* on huge strings (sort/join/filter). So the design stores kept content whole, keeps large blobs out of join/order keys, and chunks for embedding.

What this does and does **not** mean:

- **Ingest is ETL, not mirroring.** We extract the fields we care about and munge them into *our* schema; we do **not** store the raw original record verbatim (O10 resolved: no raw layer). The source carries fields we don't care about, and hoarding them is not the point — capturing the kept fields *in full* is what removes the need to revisit originals.
- **Tool outputs are not captured.** Tool *inputs* are kept; outputs are intentionally dropped (high bulk, low recall value).
- **Decouple storage from embedding.** The embedder has a small token window, so long text is chunked and mean-pooled regardless; full text is stored, bounded chunks are embedded — a ~200 KB field never threatens the embedder.
- **Large-content isolation (O11)** into a dedicated table is an optional operational optimization, not a requirement; inline storage is fine.

## Conversation Schema — Design Method & Generality

The schema is designed empirically: **point an agent at each harness's actual on-disk logs, enumerate the fields it exposes, and decide what to keep** — rather than transliterating any reference's DDL. This is how the operator built `cursor-warehouse`, and doing it against *both* Cursor and Claude Code keeps the design from being single-harness-biased.

**Core fields to capture (the must-haves):**

- **Timestamp** of each message/event.
- **Message content**, in full.
- **Role/type** (user / assistant / tool, etc.).
- **Model** used per conversation chain.
- **Subagent conversations**, included and **linked to their parent conversation**.
- **Tool calls** (inputs; not outputs).
- **Agent thinking/reasoning** *if the harness exposes it* — a nice-to-have, not required (O15).

**Harness-specific artifacts (opportunistic, O14):** whatever else a harness exposes that has recall value — e.g., Claude Code **plan documents**, and Cursor **plan-mode** documents — ingested into a shared, harness-labeled table (e.g., plan documents) when present.

**Conversation reconstruction is first-class (D21).** Every artifact — message, tool call, subagent, plan document — must be linkable back into the coherent conversation it belongs to. Finding a plan document by semantic search is far more valuable when you can see *which conversation it came from* and replay the thread around it. The linkage keys (conversation id, parent/child, ordering) are part of the core design, not an afterthought.

**Generality requirements:** preserve structural separation (don't collapse distinct objects into one blob); ingest a worst-case append-only-markdown harness cleanly (its blob lands in one field); stay harness-labeled and extensible so an unknown future harness slots in without a redesign.

## Storage

- **DuckDB** single-file warehouse.
- **Vector search** via DuckDB's VSS extension with an **HNSW** index (cosine), as in `cursor-warehouse`.
- **Location is harness-neutral**: `~/.stockroom/` (O1 resolved), XDG-aware where the platform expects it — deliberately *not* under `~/.cursor/` (which is Cursor-specific). This differs from the references, which nest the DB under a single harness's directory.

## Embeddings

- `sentence-transformers` with `all-MiniLM-L6-v2` (384-dim vectors), computed **locally** (privacy + the torch backend is why the torch exception matters).
- GPU when available, CPU fallback.
- Long text chunked and mean-pooled to one vector per source item (reusable concept from `cursor-warehouse`).
- Storage and embedding are **decoupled**: full text is stored untruncated; the embedder only ever sees bounded chunks.

## Search Surface

Three distinct skills, named for intuitiveness:

- **`sr-search`** — the friendly **entrypoint**: a smart blend of keyword (SQL `ILIKE`-style) and semantic (vector) matching, merged and ranked. This is what a user reaches for by default. It also **reasons about an appropriate output-truncation level** for the request (O13) — enough to answer, without flooding the context window.
- **`sr-semantic`** — pure vector search, for when you *know* you want meaning-based lookup. Named so the keyword-search-seeker won't grab it by mistake.
- **`sr-query`** — raw SQL against the warehouse, for power users.

## Ingest

- Scan **both harnesses'** on-disk traces: Cursor agent transcripts under `~/.cursor/projects/<workspace-slug>/agent-transcripts/.../*.jsonl`, and Claude Code's native transcripts (under `~/.claude/`; exact layout enumerated during the schema study). **Subagent** transcripts are included and linked to their parent.
- **Incremental** via per-source watermarks (mtime/path), as in `cursor-warehouse`.
- Every row is **harness-labeled** so multiple harnesses coexist cleanly.
- **Content is stored untruncated** (the fields we keep, in full). Ingest is ETL into our schema — no verbatim raw copy (O10), and tool *outputs* are not captured (inputs only).
- **v1 ingests both Cursor and Claude Code** (O12 resolved). Claude Code parsing reads the *harness's* native on-disk format — implemented **clean-room**, not by reusing `claude-warehouse`'s parser or schema.
- The ingest script "just finds what it can and ingests it" — onboarding does not require per-harness configuration in v1.
- Path resolution must handle the **WSL/Windows-mount** reality (native `~/.cursor` first, Windows-side mount fallback where applicable). See `implementation-details.md`.
- `ai-code-tracking.db` (SQLite) ingest is limited to model/labeling info (O3 resolved); attribution tables are out of v1 (D16).

## Migrations

- Numbered, **one-migration-per-file** SQL files, **inside the skill** and git-tracked, so they ship with the plugin and run on users' machines before the DB is used.
- A **`schema_version`** record (or equivalent) tracks applied migrations.
- **Lazy gate (D12):** each skill — and the nightly job — checks the schema version before touching the DB; if behind, it acquires an **exclusive lock**, applies pending migrations in order, then proceeds. If another process holds the lock (migration in progress), callers wait or back off gracefully rather than racing.
- **Preserve data; never force a full re-embed.** Embeddings are the expensive asset; migrations transform in place and must not require recomputing them.
- Forward-only (O4 resolved).
- The **session-start hook does not migrate** — it only launches the dashboard. Migration is owned by the consumers of the DB.

## Concurrency Model

DuckDB is single-writer. Multiple parallel agents/skills may read concurrently; writes (ingest, migrate) are serialized behind a lock. Readers open read-only and tolerate transient lock contention (retry/backoff). The migration lock is the strictest: exclusive, no readers mid-migration.

## Scheduling and Freshness

- **Nightly scheduled ingest + embed is the primary freshness mechanism (D14)**, installed by `sr-initialize`.
- **cron** on Linux, **launchd** on macOS. The skill must resolve the **correct absolute paths** for the user's machine (the operator's own box shows the hazard: a cron entry pinned to a slow Windows-mount path vs a fast WSL-internal path). Windows-native scheduling is out of v1 (O8 resolved).
- This is a deliberate change from the references, which lean on a session-start hook (or an under-documented launchd-only setup) for freshness.

## Hooks

A single **session-start hook launches the dashboard** and nothing else. It must be **idempotent** (port-probe; exit cleanly if already running), **fire-and-forget** (detached background process), **bounded** by the hook timeout, and **must never error**. No ingest and no migration happen in the hook.

## Dashboard

- The v1 headline UI: a local web server rendering an at-a-glance summary of usage/activity.
- Launched on session-start (per above) and on-demand via `sr-dashboard`, which prints the local URL.
- A light/stdlib server with **vendored** front-end assets (no CDN) honors the offline + supply-chain posture (O6 resolved); the exact framework is a build-time pick.
- The metrics it computes are intentionally the **substrate for the future recap**: recap ≈ those same metrics dragged through time into a time-series.

## Distribution and Packaging

- Follow the **`slobac` template**: dual `.cursor-plugin/plugin.json` + `.claude-plugin/plugin.json`, a shared top-level `skills/` tree, **no build step**, versioned by **release-please** (which syncs the version into both manifests), and published via the separate **`txrk9-agent-plugins`** marketplace repo.
- Skills live at `skills/sr-*/SKILL.md`. Unusually for that template, **one skill directory also contains the full Python app: `pyproject.toml`, `uv.lock`, the migration files, and the scripts.** This is heavier than `slobac` and is accepted as the cost of the locked-app trust property.
- **Both `.cursor-plugin` and `.claude-plugin` manifests ship from the start (O2 resolved)** — partly so the schema and tooling are continuously exercised against both harnesses rather than one.

## Skill Inventory (v1)

`sr-initialize`, `sr-search`, `sr-query`, `sr-semantic`, `sr-dashboard`. Migrations are internal machinery invoked by these, not a user-facing skill. No `sr-recap` in v1.
