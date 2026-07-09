# Stockroom — Tech Brief

*The authoritative technical context for stockroom: the stack it is built on, the load-bearing engineering decisions that shape v1, and the constraints and open questions that bound the build. Where the Product Brief says what stockroom is and why, this says how it is built.*

## What the Stack Is

Stockroom is a local Python application, managed end to end with [uv](https://docs.astral.sh/uv/), that ingests agentic-coding history into a single-file [DuckDB](https://duckdb.org/) warehouse and makes it searchable by keyword, by meaning, by raw SQL, and at a glance through a local dashboard. Semantic search is powered by `sentence-transformers` embeddings computed locally, indexed with DuckDB's VSS (HNSW) extension. The whole thing ships as a dual-manifest plugin — one payload that installs into both Cursor and Claude Code — with **no build step**: the committed layout is the install layout.

The single most important technical decision, and the reason stockroom exists as its own productized tool rather than a pile of scripts, is that it ships as a **locked uv *project***: a real `pyproject.toml` with a committed `uv.lock`, run with `uv run --frozen`. A tool that reads every one of your conversations must not be able to pull fresh, unaudited code into itself at run time. Everything is pinned and hash-verified through the lockfile — with exactly one deliberate, documented exception: **torch**, which is held outside the lock and provisioned per-machine. How that exception works is the subject of its own section below; it was the one genuinely open question (O9) and it is now resolved empirically.

This document is forward-looking. Almost no stockroom product code exists yet, so where a mature tech context would point at existing configuration ("as configured in `jest.config.js`"), this brief names the canonical configuration files that *will* be the sources of truth — `pyproject.toml`, `uv.lock`, the `schema.sql`/migration files — and describes the decisions they will encode. As the build lands, those files become authoritative and this brief should defer to them rather than duplicating their drift-prone specifics.

## Language, Runtime, and Build Tooling

Stockroom is **Python**, managed with **uv**, following the operator's `cursor-warehouse` experience. The minimum interpreter is pinned by `requires-python` in `pyproject.toml`; uv provisions a matching interpreter, so contributors do not hand-manage Python versions.

The defining shape is a **uv project**, not a collection of `uv run --script` single-file scripts. The reference tools (`cursor-warehouse`, `claude-warehouse`) run scripts via `uv run --script` with **loose PEP 723 ranges and no lockfile**, so dependencies are re-resolved fresh on essentially every run. For software that reads all of your conversations, that re-resolution is an unacceptable dependency-injection surface. Stockroom corrects this directly:

- A committed `uv.lock` pins **exact versions and records hashes** by design, so the secure path is also the reproducible one.
- Skills invoke the app through the frozen lock (`uv run --frozen` / `uv sync --frozen`), never re-resolving at run time.
- `uvx` / `uv tool run` is explicitly *not* used for the core app — it targets ephemeral published tools and does not honor a project lockfile.

**The lock must be generated hermetically.** The spike surfaced a real hazard: an ambient user-level `~/.config/uv/uv.toml` index (the operator has one pointing at a PyTorch CUDA wheel index) **leaks into project resolution**, pinning ordinary pure-Python packages to that index instead of PyPI. A shipped lockfile cannot depend on the machine that happened to generate it. Therefore the committed lock is produced with **`uv lock --no-config`**, which ignores ambient config and resolves everything from PyPI. This was verified: with `--no-config` the lock resolves entirely from `pypi.org/simple`, with hashes, and zero leakage.

There is **no compile, bundle, or transpile step**. "Build tooling" here means dependency resolution (uv) and release versioning (`release-please`, see Distribution). The canonical configuration is `pyproject.toml` plus `uv.lock`; treat them as the source of truth for the dependency set and never catalog versions elsewhere.

## The Torch Exception

`sentence-transformers` depends on **torch**, and torch is the one dependency that **must not be locked across platforms**. Cross-platform torch locking is a known dead end: the correct wheel differs by accelerator (CPU vs CUDA vs Apple MPS) and even by GPU generation, and no single pinned set is correct everywhere. This is a **hard requirement**, not a preference. The goal is therefore: *lock everything except torch, and provision torch per-machine, out of band.* O9 asked **how**; the spike (`planning/spikes/o9-torch/`) settled it.

### The Resolved Mechanism

Torch is excluded from the locked resolution entirely by overriding every torch requirement — including the transitive one from `sentence-transformers` — with an impossible environment marker:

```toml
# pyproject.toml
[tool.uv]
override-dependencies = ["torch; python_full_version < '3'"]
```

Because `requires-python` is `>=3.11`, the marker `python_full_version < '3'` is always false, so torch (and all of its `nvidia-*` CUDA transitives) never enter the resolution. Everything else locks normally. Verified result of `uv lock --no-config` against a representative dependency set (`duckdb`, `sentence-transformers`, `numpy`): **38 packages, 533 recorded hashes, all from PyPI, zero torch/CUDA/nvidia entries** — and a synced environment from that lock has no torch, so `import sentence_transformers` fails with `ModuleNotFoundError: No module named 'torch'`, which proves the exclusion is real rather than incidental.

An impossible marker is the right tool because the documented uv PyTorch integrations all do the forbidden thing: `[tool.uv.sources]` with an `explicit` index, and the `conflicts`/extras pattern, both **write torch into `uv.lock`** as platform-specific entries (the latter additionally hits a known uv bug, [#17732](https://github.com/astral-sh/uv/issues/17732), that drops transitive CUDA deps). The override keeps torch *out of the lock altogether*, which is exactly the required contract. (`sys_platform == 'never'` is a common variant of this trick but does not behave under universal resolution; the `python_full_version` form does, and is what the spike verified.)

### Provisioning Torch Out of Band

Torch is installed as a separate, explicit step after the locked environment exists:

```bash
uv sync --frozen                                              # locked deps, no torch
uv pip install torch --no-config --index <platform-wheel-url> # provide torch per-machine
```

Two non-obvious details, both proven in the spike and both load-bearing:

1. **`--no-config` is required on the torch install.** With config active, the `override-dependencies` line neutralizes even an explicit `uv pip install torch` — uv treats the request as already satisfied and installs nothing ("Audited 1 package", 0 installed). `--no-config` bypasses the project override so torch actually installs, and makes the command independent of any ambient user config. The accelerator build is then chosen by the explicit `--index` (e.g. `https://download.pytorch.org/whl/cu126` for CUDA 12.6, or `.../whl/cpu`). uv's native `--torch-backend=auto` is a candidate to evaluate at build time, but the explicit-index path is what the spike verified.
2. **A plain `uv sync`/`uv run` will *uninstall* torch.** Because torch is not in the lock, an *exact* sync (the default) treats it as extraneous and removes it. After torch is provisioned, all invocations must preserve it:
   - `uv run --no-sync …` — the standard hot-path runtime call; skips syncing entirely (fastest, torch-safe).
   - `uv sync --frozen --inexact` / `uv run --frozen --inexact …` — when a sync genuinely is needed (e.g. after a locked-dependency change), `--inexact` reconciles the locked set **without removing** out-of-lock packages like torch.

   Both were verified to leave a working torch in place; a bare exact sync was verified to delete it. The operational rule is simple: **provision torch once, then never run an exact sync.** Skills and the nightly job standardize on `--no-sync` (or `--inexact` when updating).

### Why Torch Is a Per-Machine Choice

The spike produced a concrete demonstration of why torch cannot be auto-resolved: PyPI's default torch (cu130 / 2.12 at the time of the spike) has **dropped Pascal `sm_61`**, so it loads on the operator's GTX 1070 but crashes on first kernel launch with `CUDA error: no kernel image is available for execution on the device`. The `cu126` / 2.11 wheel ships `sm_60` (forward-compatible to `sm_61` under CUDA's cubin rules) and runs correctly. The right wheel depends on the specific GPU and driver, which only the user knows. Both a **GPU run** (CUDA available, GTX 1070, 384-dim embedding) and a **CPU fallback** (`CUDA_VISIBLE_DEVICES=""`, same 384-dim result) were verified green.

The consequence for onboarding: `sr-initialize` must let the user pick the platform-appropriate index (Linux+NVIDIA → a `cu*` URL matching their driver; Apple Silicon and CPU-only → the macOS/CPU install line; never a `cu*` URL on those), provision torch with the recipe above, and then **smoke-test it** — print `torch.__version__` and `torch.cuda.is_available()`, and actually encode one string — so a wrong-wheel mismatch is caught at setup rather than at first embed.

### Verification Boundary

The spike ran on this machine only: **Linux / WSL2 / x86_64 / CUDA (GTX 1070)**, plus the CPU fallback. The packaging mechanism (override-out-of-lock, hermetic lock, out-of-band install, sync-preservation) is platform-agnostic and proven here; macOS/MPS and Windows wheel selection are *reasoned* (same recipe, different `--index`/install line) but not yet executed. Validating macOS and a fresh non-cached install is a build-time task, ideally folded into the `sr-initialize` smoke test on real target machines. The existing `cursor-warehouse` reference's initializer correctly installed gpu-less onto an M4 macbook and worked; trust that pattern.

## Storage and Concurrency

The warehouse is a **single-file DuckDB database**. Vector search uses DuckDB's **VSS extension with an HNSW index** under the cosine metric, as in `cursor-warehouse`: install/load `vss`, set `hnsw_enable_experimental_persistence = true`, and reinstall/load the extension so deletes work against a live index.

The database lives in a **harness-neutral location** — `~/.stockroom/` as the home. This is a deliberate departure from the references, which bury the DB under a single harness's directory (e.g. `~/.cursor/`); stockroom serves multiple harnesses, so its storage belongs to *stockroom*, not to any one of them.

Untruncated storage is cheap and safe here: DuckDB `VARCHAR` has no length limit (a 4 GB ceiling, UTF-8) and database files scale to terabytes. The only real cost is *operating* on huge strings, so the design keeps large blobs **out of join and sort/order keys** and chunks text for embedding — but stores the kept content whole. (See Faithful Capture.)

Concurrency follows DuckDB's model: **single writer, concurrent readers.** Writers (ingest, embed, migrate) are serialized behind a lock; readers (search, dashboard, query) open read-only and tolerate transient contention with retry/backoff rather than failing. The migration lock is the strictest — exclusive, with no readers mid-migration. The choice of lock primitive is a build-time detail (see Open Build-Time Questions).

## Faithful Capture

Faithful recall is the product's reason to exist, and it rests on **two distinct ideas that must not be conflated:**

- **No truncation at rest.** The fields stockroom chooses to keep — message content, prompts, tool inputs — are stored *in full*. Never a 2,000-character stub. The references hard-cap stored content (measured: `text_content`/`user_query` at 2,000 chars, `tool_input` at 500, with ~17% of messages clipped), which repeatedly forced the operator back to raw transcripts. Stockroom does not.
- **Smart truncation at read.** Skills deliberately truncate *output* so that retrieving a 200 KB field never floods an agent's context window. The `sr-search` entrypoint reasons about an appropriate output level for the request. Truncation is thereby repositioned from a destructive storage default into a deliberate read-time feature.

Two structural commitments follow:

- **Ingest is ETL, not mirroring.** Stockroom extracts the fields it cares about and reshapes them into its own schema. There is **no verbatim raw layer** and **tool *outputs* are not captured** (inputs only) — they are high-bulk, low-recall-value. Faithfully keeping the *kept* fields in full is what removes the need to revisit originals; hoarding every source field is not the point.
- **Storage is decoupled from embedding.** The embedder has a small token window, so long text is chunked and mean-pooled regardless of how it is stored. Full text is stored untruncated; only bounded chunks are ever embedded, so a ~200 KB field never threatens the embedder. Isolating large bodies into a dedicated content table is an optional later optimization, not a v1 requirement — inline storage is fine.

## Embeddings

Embeddings use **`sentence-transformers` with `all-MiniLM-L6-v2`** (384-dim vectors), computed **locally** — no external API, ever. GPU is used when available, with CPU fallback. Long text is **chunked (~800 chars, ~100 overlap) and mean-pooled** to a single vector per source item, a reusable approach from `cursor-warehouse` (`scripts/embed.py`). Vectors are stored as `FLOAT[384]` and indexed with HNSW (cosine).

The local-embedding requirement is *why the torch exception matters*: the embedder's backend is torch, so the locked-app-vs-platform-torch tension is unavoidable and had to be resolved (it is — see The Torch Exception). The embedding pipeline is the primary consumer of the torch provisioning, and the nightly job re-embeds new content incrementally.

## Search Surface

Three skills, named for intuitiveness, sit over the warehouse (D9):

- **`sr-search`** — the friendly **entrypoint**: a blend of keyword (SQL `ILIKE`-style) and semantic (vector) matching, merged and ranked. It is what a user reaches for by default, and it determines the right kind of lookup to service the user's question (pure SQL if you can! Vector if you can't - or a blend if you need it!) reasons about an appropriate output-truncation level for the request — enough to answer without flooding the context window.
- **`sr-semantic`** — pure vector search, for when meaning-based lookup is explicitly wanted. Named so that someone reaching for plain keyword search won't grab it by mistake.
- **`sr-query`** — raw SQL against the warehouse: the power-user escape hatch, and the proof that the data is genuinely yours to interrogate.

Keyword matching runs over the untruncated stored content; semantic matching runs over the HNSW vector index. Because content is stored whole, what a search returns is the real exchange (trimmed at read time), never a stored stub.

## The Conversation Schema

The schema is designed **empirically**: point an agent at each harness's actual on-disk logs, enumerate the fields it exposes, and decide what to keep — rather than transliterating any reference's DDL. Doing this against *both* Cursor and Claude Code is what keeps the design from being single-harness-biased. This brief fixes the schema's **design and contract**; the concrete side-by-side field enumeration against real logs, and the resulting locked table DDL, are the **first Phase 1 build task**, done test-first (see Testing Process). `cursor-warehouse`'s schema may be reused freely; `claude-warehouse`'s may not (see Clean-Room Boundary).

**Intended shape — a normalized, harness-labeled split** (a commonplace pattern, reproduced independently): roughly `sessions`, `messages`, `tool_calls` (inputs only), a harness-labeled `plan_documents` table, `embeddings`, and a `_sync_state` watermark table. Every row carries a `harness` label so multiple harnesses coexist cleanly and a future harness slots in without re-architecture.

**Core captured fields (the must-haves, likely cross-harness invariants):**

- Timestamp of each message/event.
- Message content, in full.
- Role/type (user / assistant / tool, …).
- Model used **per message** (Claude Code & Cursor allow switching models mid-conversation).
- **Subagent conversations, linked to their parent conversation.**
- Tool calls — **inputs only**, never outputs.

**Conversation reconstruction is first-class, not an afterthought.** Every artifact — message, tool call, subagent, plan document — must be linkable back into the coherent conversation it belongs to. A plan document found by semantic search is far more useful when you can see which conversation produced it and replay the thread around it. The linkage keys — conversation id, parent/child, ordering, the subagent↔parent edge, model-per-chain — are part of the core design. A stable **message identity contract** (e.g. `cursor-warehouse`'s `uuid = {session_id}:{line_idx}`) underpins embed/search and must be explicit.

**Harness-specific artifacts are opportunistic:** whatever else a harness exposes that has recall value may be ingested. For example, "plan documents" - Claude Code **plan documents**, Cursor **plan-mode** documents — lands in the shared, harness-labeled `plan_documents` table, keyed to its conversation, when present. Cross-harness invariants are prioritized over harness-specific artifacts - but if a harness has something that's genuinely unique *and* valuable, it should be ingested (perhaps into its own table, with its own linkage keys).

**Generality requirements:** preserve structural separation (don't collapse distinct objects into one blob); ingest a worst-case append-only-markdown harness cleanly (its blob lands in one field); stay harness-labeled and extensible. These are the properties the build's enumeration step must not violate.

This is a clean break from the references in substance: richer linkage (subagent↔parent, model-per-chain, plan documents, explicit reconstruction keys), no truncation, no raw mirror, no tool outputs.

## Ingest

Ingest scans **all known harnesses' on-disk traces** and reshapes them (ETL) into the schema, storing kept content untruncated:

- **Cursor:** agent transcripts under `~/.cursor/projects/<workspace-slug>/agent-transcripts/<session-id>/<session-id>.jsonl`, with subagents under `.../subagents/`. Model/labeling enrichment may read the SQLite `~/.cursor/ai-tracking/ai-code-tracking.db`, limited to what model/labeling needs — attribution tables stay out of v1.
- **Claude Code:** its native transcripts (under `~/.claude/`; exact layout enumerated during the schema-study build step). Parsing is **clean-room** — it reverse-engineers the *harness's* public on-disk format, never `claude-warehouse`'s parser or schema.

For both, if there is a public document that describes the schema, it should be located and used instead of re-reverse-engineering.

Operational properties: **incremental** via per-source watermarks (`last_mtime`, `last_path`), with a `--full` reset; **every row harness-labeled**; **subagents included and linked to their parent**. v1 ingest "just finds what it can and ingests it" — no per-harness configuration required during onboarding.

## Migrations

A real migration system is a headline productization feature and a core promise ("doesn't break your data"); `cursor-warehouse` has none, and retrofitting one is painful, so it lands early (Phase 1).

- **Numbered, one-migration-per-file SQL**, **inside the skill** and git-tracked, so they ship with the plugin and run on users' machines before the DB is used.
- A **`schema_version`** record tracks applied migrations.
- **Lazy gate:** each skill — and the nightly job — checks the schema version before touching the DB; if behind, it acquires an **exclusive lock**, applies pending migrations in order, then proceeds. If another process holds the lock, callers wait or back off rather than racing.
- **Forward-only**.
- **Preserve data; never force a full re-embed.** Embeddings are the expensive asset; migrations transform in place and must not require recomputing them.
- The **session-start hook never migrates.** Migration is owned by the consumers of the DB (skills, nightly job), not by the hook.

## Freshness, Scheduling, and Hooks

**Nightly scheduled ingest + embed is the primary freshness mechanism**, installed by `sr-initialize`: **cron** on Linux, **launchd** on macOS. Windows-native scheduling is out of v1; under WSL this means Linux cron. The installer **must resolve correct absolute paths** for the machine — the operator's own box is the cautionary example, with a legacy cron entry pinned to a slow Windows-mount path instead of the fast WSL-internal one. This is a deliberate change from the references, which lean on a session-start hook (or an under-documented launchd-only setup) for freshness.

A **single session-start hook launches the dashboard and nothing else.** It must be **idempotent** (probe the port; exit cleanly if already running), **fire-and-forget** (detached background process), **bounded** by the hook timeout, and it **must never error**. No ingest and no migration happen in the hook — those are the nightly job's and the skills' responsibility. This discipline is what keeps session start instant and safe.

## The Dashboard

The dashboard is the v1 headline UI: a **local web server** rendering an at-a-glance summary of usage and activity. It launches on session start (via the hook above) and on demand via `sr-dashboard`, which prints the local URL. The metrics it computes are intentionally the **substrate for the future recap** — recap is reconceived as those same metrics dragged through time into a time-series, not a separate feature.

It is a **light/stdlib server with vendored front-end assets — no CDN**, honoring the offline and supply-chain posture; the exact server/front-end framework is a build-time pick. There is **no formal design system** (no Figma, design tokens, Storybook, or component library) and none is planned for v1; the UI is a self-contained local analytics page whose assets are vendored into the repo. Uses port `6767`.

## Distribution and Packaging

Distribution follows the **`slobac` dual-manifest template**: a `.cursor-plugin/plugin.json` and a `.claude-plugin/plugin.json`, a shared top-level `skills/` tree, **no build step** (committed layout = install layout), versioned by **release-please** (which syncs the version into both manifests), and published through the separate **`txrk9-agent-plugins`** marketplace repo. **Both manifests ship from the start** — partly so the schema and tooling are continuously exercised against both harnesses rather than one.

Skills live at `skills/sr-*/SKILL.md`. The v1 inventory is **`sr-initialize`, `sr-search`, `sr-query`, `sr-semantic`, `sr-dashboard`**; migrations are internal machinery, not a user-facing skill, and there is no `sr-recap` in v1. Unusually for the template, **one skill directory also contains the full Python app** — `pyproject.toml`, `uv.lock`, the migration SQL files, and the scripts. This is heavier than vanilla `slobac` and is accepted as the cost of the locked-app trust property. Invocation differs by harness (Cursor `/<skill>` vs Claude `<plugin>:<skill>`); the exact `/sr-*` forms are verified empirically at build. Dev-only files under `.cursor/` are **not** shipped as plugin payload.

## Environment Setup

To work on stockroom:

- **uv** must be installed ([uv](https://docs.astral.sh/uv/)); it provisions the interpreter pinned by `requires-python`.
- **Locked dependencies:** `uv sync --frozen` from the committed `uv.lock`. **Regenerate the lock hermetically** with `uv lock --no-config` so ambient user config cannot leak in (see Language, Runtime, and Build Tooling).
- **Torch** is provisioned separately and per-machine, then preserved across syncs — see The Torch Exception for the exact recipe and the don't-run-an-exact-sync rule.

On a user's machine, `sr-initialize` automates the equivalent: prerequisite checks, platform/accelerator detection, torch provisioning + smoke test, nightly scheduler install with correct absolute paths, and a first full ingest + embed.

## Testing Process

All code work follows the workspace's **test-driven development rule**: tests are written first (stub suites/cases and interfaces, implement the tests to fail, then write code to pass). The whole suite is run before any work is considered done, and full test output is read rather than filtered. The test framework is a build-time choice (Python convention points to `pytest`); once it exists, its configuration in `pyproject.toml` is the source of truth and this brief should defer to it.

Two areas warrant explicit, deliberate test design when they are built:

- **The schema/ingest enumeration** — the first build task — is the place to encode fixtures from real (and pathological) Cursor and Claude Code transcripts, so faithful capture, linkage, and harness-generality are *proven*, not assumed.
- **Migrations and concurrency** — exercise the lazy gate, the exclusive lock, forward-only application, and graceful reader degradation under simulated parallel access, because "never corrupts the warehouse" is a promise that must be tested, including across a schema-changing upgrade.

## Clean-Room Boundary

- **`cursor-warehouse`** is the operator's own work (MIT). Its *original* code (where such code exists and is not a mere port/copy of `cladue-warehouse`) may be **freely ported, adapted, and relicensed** into stockroom under AGPLv3 — the DuckDB+VSS+HNSW stack, the embedding/chunking approach, the watermark sync, the torch-smoke pattern, the Cursor source-layout knowledge. Because `cursor-warehouse` is itself a port of `claude-warehouse`, prefer reimplementing anything that is obviously a thin transliteration of the upstream, to keep the boundary honest.
- **`claude-warehouse`** is third-party (MIT, by Stéphane Derosiaux). **No code, no schema DDL, and no unique/novel ideas may be copied** — only generally-public, commonplace concepts that would appear in any tool of this kind. Claude Code support is built by reverse-engineering the *harness's* public on-disk format, never by reading `claude-warehouse`.

## Open Build-Time Questions

These are technical decisions deliberately left to the build; none blocks the design, and none is a scope question (all scope items are settled in the brainstorm decision log).

- **Schema field enumeration + locked DDL** — the first Phase 1 task: enumerate real Cursor and Claude Code formats side by side and lock the tables, test-first, honoring the design in The Conversation Schema.
- **Migration lock primitive** — advisory lock table vs file lock on DuckDB, and the exact reader wait/backoff semantics during a migration.
- **Dashboard framework** — the specific stdlib/light server and vendored front-end stack.
- **Torch provisioning ergonomics** — whether to adopt uv's `--torch-backend=auto` alongside the proven explicit-`--index` path, and validating macOS/MPS and a cold (non-cached) install on real target machines.
