# System Patterns

## How This System Works

Stockroom is forward-looking — almost no product code exists yet, so this document is **lightly seeded from the planning docs and is expected to accrete** as the build reveals which patterns actually hold. The mental model needed before touching anything:

- The central trust decision is that stockroom ships as a **locked uv *project*** (not loose `uv run --script` files): everything pinned and hash-verified through a committed `uv.lock` — **except torch**, the single deliberate exception.
- The warehouse is a **single-file DuckDB** database in a **harness-neutral** home (`~/.stockroom/`), not buried under any one harness's directory.
- **Faithful capture is the reason the product exists**: kept fields are stored *whole* (no truncation at rest); truncation exists *only at read time*. Conflating these two is the exact mistake the reference tools made.
- Ingest is **ETL, not mirroring**: kept fields reshaped into stockroom's schema, **tool inputs only** (no outputs), no verbatim raw layer.
- The schema is **harness-labeled** (one shared set of tables, a `harness` column per row) and is designed **empirically** from real logs, not transliterated from any reference.
- **Migrations are first-class from Phase 1** (forward-only, `schema_version` record, lazy gate, exclusive write lock, concurrency-safe reader degradation). "Never break your warehouse" is a tested promise.
- **Hook discipline**: the session-start hook *only* launches the dashboard — never ingests, never migrates, never errors.

Memory-bank strategy: the rich `planning/` docs are authoritative during the build; durable knowledge accretes here, and the docs are distilled away and deleted at the final roadmap step (see `productContext.md` / `techContext.md` cut gates).

## Locked uv project, torch held out of the lock

The load-bearing packaging pattern. Lock everything hermetically with `uv lock --no-config`; exclude torch via an impossible environment-marker override (`override-dependencies = ["torch; python_full_version < '3'"]`) so it never enters the lock, then provision it per-machine out of band (`uv pip install torch --no-config --index <wheel-url>`). **After torch is installed, never run an exact sync** (`uv run --no-sync`, or `--inexact` when a sync is genuinely needed) — a bare sync deletes it. Local dev iteration (`make sync`, `make lock`, `make test`, etc.) is via the root [`Makefile`](../Makefile). Proven end-to-end in `planning/spikes/o9-torch/`; full rationale in tech-brief → "The Torch Exception".

## No truncation at rest; truncation is a read-time feature

Kept content (prompts, responses, tool inputs) is stored in full. Output truncation is applied only at read time (chiefly in `sr-search`), sized to answer without flooding the caller's context window. Storage-time caps are the failure mode stockroom exists to correct — do not reintroduce them.

## Harness-labeled schema, designed empirically

One shared set of tables (sessions, messages, tool_calls inputs-only, embeddings, `_sync_state`), every row carrying a `harness` column — never per-harness tables. Conversation reconstruction is first-class (conversation id, parent/child, ordering, subagent↔parent edge, model grain) atop a stable message-identity contract. Concrete DDL is derived test-first from real Cursor + Claude Code logs (the first Phase 1 task). (`plan_documents`, named in the original brief, was **dropped** during milestone-1 enumeration — no harness emits a plan-document record; `TodoWrite` lists already live in `tool_calls.tool_input`.)

## One meaning per field (cross-harness semantic uniformity)

**Every column means exactly one thing, independent of harness.** Only the *extraction* may differ per harness, and extraction MUST yield that one meaning. Never "`ordinal` is X for Cursor but Y for Claude" — that rots the moment a 3rd/4th harness lands. If a value cannot be made to mean the same thing everywhere, it does **not** get a shared column: it goes to a clearly-labeled `source_*` provenance column or is dropped. Identity is uniform by construction (`message_id = {session_id}#{ordinal}` for all harnesses, a deterministic surrogate; native ids like Claude's `uuid` are demoted to provenance, never joined on). Where a value is genuinely only available at a different grain per harness (e.g. model — per-message for Claude, per-conversation for Cursor), use **separate grain-specific columns** (`messages.model` vs `sessions.models`) and let each harness populate only the grain it actually has — the other is honestly NULL. We never fabricate or back-fill a grain we don't have.

## Typed columns for queryable data; JSON only for irreducible heterogeneity

DuckDB queries JSON (`->`, `->>`, `json_extract`) but **stores it as text (parsed per access) and has no JSON-path indexing** — it's a columnar engine that leans on full-scan + zonemaps, not indexes. So **never JSON-blob a value you want to filter, aggregate, or index.** First-class metrics get real typed columns (columnar, compressed, zonemapped, self-documenting): token usage is four `BIGINT` columns on `messages`, not a `usage` blob. Small sets use a native DuckDB `LIST` (`sessions.models` is `VARCHAR[]`), not JSON. JSON is reserved for the *one* irreducibly heterogeneous fidelity payload — `tool_calls.tool_input` (shape varies per tool, stored whole, never aggregated on internal keys).

## Thinking is not captured (by design)

We deliberately do **not** store model reasoning/"thinking". Rule: *if a harness lets us separate thinking from the response, we separate it and drop it; if it doesn't, we accept whatever is folded into `text`.* Claude emits explicit `thinking` blocks → dropped (we keep only `text`). Cursor has no separate thinking block → its single `text` channel is kept as-is. There is no `thinking` column, and there should never be one.

## Dual-manifest plugin, no build step, engine inside the `sr-search` skill

Ships from the `slobac` template as a `.cursor-plugin/plugin.json` + `.claude-plugin/plugin.json` over a shared `skills/` tree, **committed layout = install layout** (no build), versioned by release-please which syncs the version into both manifests. Both manifests ship from day one so both harnesses are continuously exercised.

**The full Python engine lives inside one real skill — `skills/sr-search/`** (`pyproject.toml`, `uv.lock`, `src/stockroom/`, `tests/`, and later migration SQL). This is heavier than vanilla `slobac` (whose app sits at repo root) and is the accepted cost of the locked-app trust property. `sr-search` (the core entrypoint) is the chosen host purely for coherence — resolution is plugin-root-relative (see next pattern), so the host dir is invisible to consumers. The engine project sets `[tool.uv] package = false` (run-in-place; deps locked, stockroom itself never built/installed), honoring no-build-step.

**Skeleton-skill convention:** a skill directory may ship before its behavior exists, carrying a `SKILL.md` with real front-matter and a body that states the dir's purpose and that the behavior is built in a named later phase. This is an honest placeholder, explicitly *not* a dummy — it is how the engine-bearing skill exists from Phase 0 while its search behavior lands in Phase 2.

## Cross-skill resource resolution (PLUGIN_ROOT, cribbed from `cursor-warehouse`)

`cursor-warehouse`'s own invention (safe to reuse — not `claude-warehouse`-derived). Sibling skills locate the shared engine **once on startup** via the harness-provided plugin-root env var (`CURSOR_PLUGIN_ROOT` in Cursor; the Claude equivalent — verify exact name empirically per harness at build), with a `find -L` fallback that traverses symlinked dev installs. Then invoke through the **torch-safe** contract — never an exact sync:

```bash
APP_DIR="${CURSOR_PLUGIN_ROOT:+$CURSOR_PLUGIN_ROOT/skills/sr-search}"
if [ -z "$APP_DIR" ] || [ ! -d "$APP_DIR" ]; then
  APP_DIR="$(dirname "$(find -L ~/.cursor/plugins -path '*/stockroom/*/skills/sr-search/pyproject.toml' 2>/dev/null | head -1)")"
fi
uv run --project "$APP_DIR" --no-sync python -m stockroom.<entrypoint> ...
```

## Layered licensing (REUSE/SPDX): AGPL on code, PPL-S on prompts

Intentional and load-bearing (mirrors `../slobac/REUSE.toml`). A root `REUSE.toml` + `LICENSES/*.txt`, enforced by `reuse lint` in CI/tests (not advisory). AGPLv3 is the **battle-tested explicit base on all code**; the experimental **PPL-S is layered over prompt-shaped content** (`skills/**` — `SKILL.md`, references), and code-shaped paths within `skills/**` (`*.py`, `*.sql`, `pyproject.toml`, `uv.lock`, `tests/**`) are **re-asserted AGPL**. Worst case prompts are still AGPL; best case they are PPL-S-clarified too. Relies on REUSE's last-matching-annotation-wins ordering: base AGPL → `skills/**` PPL-S → code-within-skills AGPL → vendored `.cursor/**` NOASSERTION.

## Two-layer warehouse lock behind a single open() chokepoint

Every consumer reaches the DuckDB warehouse through one function —
[`stockroom.warehouse.open(read_only=…)`](../skills/sr-search/src/stockroom/warehouse.py) — never by connecting directly. The lazy migration gate lives *inside* `open()`, so no consumer can touch an un-migrated DB and the session-start hook stays migration-free simply by never calling it. Concurrency is two cooperating locks, each with one job:

- **Coordination layer** — an `fcntl.flock(LOCK_EX)` on a sidecar `~/.stockroom/.warehouse.lock`. The single-writer/migrator token; a process takes it before opening DuckDB read-write. Readers never take it. OS auto-releases it on process death, so a crashed migrator can't wedge the warehouse (no TTL/reaper needed).
- **Data layer** — DuckDB's own file lock (RW exclusive, RO shared). The real data-integrity guarantee; the flock exists only to approach it in an orderly, herd-free way.

Read surfaces (`sr-query` today; `sr-search`/`sr-semantic`/dashboard later) open `read_only=True` and let **DuckDB itself reject writes** — there is no app-level statement allow/deny-list. Immutability is enforcement-for-free from the open mode, so a query surface only has to translate the resulting `duckdb.Error` into a clean message ([`stockroom.query`](../skills/sr-search/src/stockroom/query.py)). Readers are lock-free at the coordination layer: they open RO and degrade against the data layer via bounded exponential backoff that catches DuckDB's open-time `IOException("Could not set lock")` and terminates in a typed `WarehouseBusyError` rather than blocking forever. Writers hold the flock for the connection's lifetime (released via `weakref.finalize` — `duckdb` connections reject attribute assignment but support weakrefs). Migration bookkeeping (`schema_version`) is runner-owned and created *outside* `0001`, keeping the locked initial DDL + golden snapshot untouched. The primitive is POSIX-only (`fcntl`); v1 targets WSL/macOS, native Windows is out of scope (fails fast at `import fcntl`). Full rationale: `memory-bank/active/creative/creative-warehouse-concurrency-locking.md` (until archived).

## VSS loaded at the chokepoint; the index is a migration; INSTALL is off the hot path

The DuckDB `vss` extension is loaded **at the `warehouse.open()` chokepoint**, not in migration SQL. `ensure_vss(con)` (`LOAD vss`, install-on-missing, then the per-connection `SET hnsw_enable_experimental_persistence`) runs on *every* connection `open()` returns — read-write and read-only alike (both verified to succeed on RO; `LOAD`/`SET` are session-level, not DB writes). This is the same place that already owns the lazy migration gate and per-connection setup, so it is the natural home. The HNSW index itself lands as a normal forward-only migration (`0003`), keeping the "schema changes only via numbered migrations" invariant — but the migration is *thin*: it `CREATE INDEX … USING HNSW` only and never `INSTALL`/`LOAD`s, because the network `INSTALL` (the one supply-chain-sensitive op) must stay out of shipped DDL and off the runtime read path. The migration runner stays extension-agnostic; "vss is loaded" is a caller-established precondition (chokepoint in production, `ensure_vss` in fixtures), exactly as the runner already assumes "caller holds the flock." Rationale: `creative-vss-provisioning-and-index.md`.

## Embeddings: a second chokepoint writer, per-chunk and incremental

`stockroom.embed` is the **second** read-write consumer of the warehouse (besides ingest), and like ingest it goes through `warehouse.open(read_only=False)` — so the single-writer flock contract is preserved by construction (no concurrent writers). It stores **one vector per chunk** (`chunk_index = 0..N-1`), not a mean-pool: lossless and best for long-tail recall, at the cost of an m2 obligation to dedup chunk hits to one per owner. Incrementality is two cooperating halves with **no new schema column**: (A) select messages lacking an `embeddings` row for the *current* `embed_model` (covers new content + model change), and (B) a cascade-delete of a session's message embeddings inside `ingest.writer`'s existing delete-then-insert (covers edits — derived data is invalidated with its source). A subtlety the PK forces: `embeddings`'s PK is `(harness, owner_table, owner_id, chunk_index)` — it excludes `embed_model`, so two models cannot coexist for the same owner+chunk; (re-)embedding a selected owner therefore *replaces* its vectors. Testability mirrors the engine-wide `con`/dependency-injection precedent: an injected `Encoder` keeps the pipeline torch-free under CI; the real `BgeEncoder` is the lone `importorskip`-gated edge. Rationale: `creative-{chunk-storage-grain,incremental-reembed-detection,embedding-owner-grain,embedding-model-selection}.md` (archived with the m1 sub-run).

## Semantic search: index KNN → over-fetch → max-sim owner dedup, with an asymmetric query prefix

The read counterpart to per-chunk storage. [`stockroom.semantic`](../skills/sr-search/src/stockroom/semantic.py) (`python -m stockroom.semantic`) is a read-only surface that reuses the m1 `Encoder`/`BgeEncoder` and the `0003` cosine HNSW index. Two coupled decisions make per-chunk storage pay off at read time:

- **Over-fetch then dedup, not `GROUP BY MIN`.** Because m1 stores **one vector per chunk**, a single owner message can occupy several of the nearest chunk hits. A `GROUP BY owner MIN(distance)` would dedup perfectly but defeat the HNSW top-k acceleration. Instead the surface keeps the index-accelerated `ORDER BY array_cosine_distance(…) LIMIT (limit * OVERFETCH)` and dedups **in Python** to the nearest chunk per `(harness, owner_id)` (the hits arrive ascending, so first-seen = best) — uses the index *and* discharges the max-sim owner grain m1 deferred. `OVERFETCH` is a tunable, not an architectural seam.
- **Asymmetric query prefix.** bge-small-en-v1.5 is an asymmetric retriever: passages are embedded with **no** prefix (m1), but the **query** is prepended with bge's instruction prefix (`QUERY_PREFIX`) — the cross-corpus spike measured ~+0.037 MRR@10 for it. A query is embedded as a **single** vector (never chunked — chunking is a storage concern; a query is one point). The prefix is threadable (`query_prefix=""`) so the deterministic `FakeEncoder` can land a query exactly on a stored chunk for unit tests.

Output is a ranked table whose `score` is cosine **similarity** (`1 - distance`) and whose `text` is a fixed-width single-line **display** preview only — this is *not* the no-truncation-at-rest violation: the full text stays whole in the store and in the returned `SemanticHit`. Context-aware read-time truncation is the separate m3 (`sr-search`) feature; `semantic` is named so a keyword-search seeker doesn't grab it by mistake.

## Ingest is per-harness clean-room parsers feeding a harness-neutral normalized model

The ETL ([`stockroom.ingest`](../skills/sr-search/src/stockroom/ingest/)) is shaped so the harness-specific knowledge lives in exactly one place per harness and nowhere else. Each parser (`cursor.py`, `claude.py`) reverse-engineers its harness's own on-disk format and emits the same three harness-neutral dataclasses (`NormalizedSession`/`Message`/`ToolCall` in `model.py`); the `writer` is the only code that touches SQL, and the orchestrator just wires discover → parse → (enrich) → write → watermark. Parsers depend only on `model` + stdlib — pure and unit-testable, no DB, no I/O beyond the file handed to them. Consequence: adding a 3rd harness is "write one parser to the model contract," and the duplicated-looking JSONL line readers in the two parsers are *intended* self-containment, not a DRY defect — each format is decoded independently.

The hard correctness invariant is **uniform positional identity built over the *kept* set**: `message_id = {session_id}#{ordinal}` with a dense 0-based ordinal over kept messages; dropped/ignored records consume no ordinal. Parent linkage is reconstructed differently per harness but means the same thing — Cursor is linear (previous-kept), Claude walks the branching `parentUuid` tree to the nearest *kept* ancestor (native `uuid` demoted to `source_uuid` provenance, never joined on). Claude record handling is **allowlist-driven** (kept types are explicit; unknown types are ignored without error) precisely because real logs carry far more record types than any fixture set. Idempotency is delete-then-insert per `(harness, session_id)`; incrementality is a `(mtime, path)` `_sync_state` watermark per `(harness, source_root)` with a `--full` bypass.

This whole reconstruction — every ordinal, `parent_id`, drop, token value, and subagent edge — is locked by a **golden output snapshot** ([`tests/fixtures/ingest/expected_rows.json`](../skills/sr-search/tests/fixtures/ingest/expected_rows.json)) generated by the test's *own* query helper and asserted byte-for-byte. This is the third instance of the project's load-bearing snapshot discipline (m1 `0001` schema snapshot, m2 `open()` DDL guard, m3 ingest output): the generator and the assertion share a code path, so they cannot silently diverge, and any intentional parser change shows up as a reviewed diff to the golden file.

## Workspace identity vs. real path: verify-don't-invert cwd recovery

The canonical application of "one meaning per field" to the harness project-dir.
Both harnesses file conversations under an **encoded slug** in which every
non-alphanumeric character of the real path collapses to `-` (separators *and*
`.`, `_`, …). That encoding is many-to-one, so it **cannot be inverted** — the
old `'-' -> '/'` decode *fabricated* paths (`lite-rpg` → `lite/rpg`). The fix is
two single-meaning columns:

- **`sessions.project_id`** — the slug stored **verbatim**. It is an *id*, not a
  path: always present, lossless, the correct grouping key ("group my
  conversations by project"). Never decoded, never fabricated.
- **`sessions.cwd`** — the real project-root path, **best-effort, honestly NULL
  when unknown**, never fabricated. Grouping rides on `project_id`, so a NULL
  `cwd` costs nothing.

`cwd` is recovered by **verifying, not inverting**: you can't invert `encode`,
but you can compute it forward, so a candidate path is accepted only when
`encode_for(harness, candidate) == slug` (exact by construction; failure mode is
a clean NULL). Claude supplies its authoritative record `cwd`; Cursor (which
carries none) re-encode-and-matches over **in-band transcript paths** —
deletion-proof, FS-free, deterministic, so the golden stays machine-independent.
The transform (`stockroom.ingest.paths`) was locked **empirically** against real
history (`planning/spikes/cwd-recovery/`): the slug alphabet is exactly
`[A-Za-z0-9-]`; Cursor strips the leading separator, Claude keeps it. The
guarantee is enforced corpus-wide by a **round-trip invariant** test —
`encode_for(harness, cwd) == project_id` for every non-NULL `cwd` — making a
fabricated path structurally impossible to store. This shipped as migration
`0002` (the framework's first real schema-changing, data-preserving upgrade;
structural, no backfill — re-ingest repopulates), with `0001` and its snapshot
frozen. **Verify-don't-invert generalizes to any future lossy harness encoding.**

## Clean-room boundary, with a build-time provenance procedure

- **`claude-warehouse`** (third-party MIT): no code, no schema DDL, no unique ideas — ever. Claude Code support is reverse-engineered from the *harness's own* public on-disk format. Keeping `claude-warehouse` out of view is the *correct* posture, not a limitation.
- **`cursor-warehouse`** (operator's MIT): may be ported and relicensed to AGPLv3 — **but it is itself a port of `claude-warehouse`**, so without the upstream visible you cannot reliably tell which parts are genuinely original. The most portable pieces (the cross-harness engine: DuckDB/VSS, embedding/chunking, schema, watermark) are exactly the parts most likely to be upstream transliterations.
- **Operating procedure:** do not keep `cursor-warehouse` open by default, and do not copy from it speculatively. Reimplement cross-harness engine bits from the briefs/spike and first principles. When a specific piece would genuinely help, **request it from the operator**, who identifies what is genuinely original and therefore AGPL-able — in practice mostly the **torch work**. Schema is derived empirically regardless, which moots its provenance.
