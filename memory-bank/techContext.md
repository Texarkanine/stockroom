# Tech Context

Stockroom is a local **Python** application managed end-to-end with **uv**, storing agentic-coding history in a single-file **DuckDB** warehouse with local **`sentence-transformers`** embeddings indexed via DuckDB's **VSS/HNSW** extension. It ships as a **dual-manifest** Cursor/Claude-Code plugin with **no build step** (committed layout = install layout).

**Authoritative source (until the end-of-roadmap cut): [`planning/tech-brief.md`](../planning/tech-brief.md).**

This file is intentionally thin right now and is designed to **accrete**. The tech brief is explicitly forward-looking; as each roadmap phase lands real configuration, this file gains pointers to those canonical artifacts (`pyproject.toml`, `uv.lock`, `release-please-config.json`, the migration SQL, the test config) and the brief's role correspondingly shrinks. **Cut gate:** at the end-of-roadmap distillation, this file must stand alone with zero references into `planning/`.

## Environment Setup

uv provisions the interpreter pinned by `requires-python`. Locked deps via `make sync` (or `uv sync --frozen --no-config` in `skills/sr-search/`); **regenerate the lock hermetically** with `make lock` (or `uv lock --no-config`) so ambient user config can't leak in. **Torch is the one exception** — held out of the lock, provisioned per-machine out of band, and preserved across syncs (never run an exact sync after installing it). Recipe proven in [`planning/spikes/o9-torch/`](../planning/spikes/o9-torch/); full detail in tech-brief → "The Torch Exception". The canonical project config is [`skills/sr-search/pyproject.toml`](../skills/sr-search/pyproject.toml) (the `requires-python` floor, the `[tool.uv] override-dependencies` torch marker, and `package = false`) with its hermetic [`skills/sr-search/uv.lock`](../skills/sr-search/uv.lock); the torch-safe run contract is documented in the [root README](../README.md).

## Build Tools

uv for dependency resolution (no compile/bundle/transpile step) and `release-please` for version syncing into both plugin manifests. Canonical config: [`skills/sr-search/pyproject.toml`](../skills/sr-search/pyproject.toml) + [`uv.lock`](../skills/sr-search/uv.lock), and [`release-please-config.json`](../release-please-config.json) + [`.release-please-manifest.json`](../.release-please-manifest.json) (writes `$.version` into both `plugin.json` manifests). CI is [`.github/workflows/ci.yml`](../.github/workflows/ci.yml); release automation is [`.github/workflows/release-please.yaml`](../.github/workflows/release-please.yaml). **Local iteration** is via the root [`Makefile`](../Makefile) (`make help` lists sync/lock/test/lint/format/reuse/ci targets; it wraps the engine-dir `uv` invocations with `--no-config` and torch-safe `--no-sync`).

## Warehouse Schema

The locked, harness-labeled DuckDB data contract is authored as the first
migration: [`skills/sr-search/src/stockroom/migrations/0001_initial_schema.sql`](../skills/sr-search/src/stockroom/migrations/0001_initial_schema.sql)
(five tables: `sessions`, `messages`, `tool_calls`, `embeddings`, `_sync_state`).
It is the single source of truth for table shape; the schema-contract tests in
[`skills/sr-search/tests/test_schema_0001.py`](../skills/sr-search/tests/test_schema_0001.py)
pin it, and the introspected golden snapshot
[`skills/sr-search/tests/fixtures/schema/0001_snapshot.json`](../skills/sr-search/tests/fixtures/schema/0001_snapshot.json)
makes any DDL change a conscious, reviewed act. Durable native-format transcript
samples for later ingest work live under
[`skills/sr-search/tests/fixtures/transcripts/`](../skills/sr-search/tests/fixtures/transcripts/).

The forward-only migration framework that applies this SQL landed in
milestone 2. Consumers never connect to DuckDB directly: they go through the
single chokepoint [`stockroom.warehouse.open()`](../skills/sr-search/src/stockroom/warehouse.py),
which resolves the harness-neutral home (`~/.stockroom/`, overridable via the
`STOCKROOM_HOME` env var), runs a double-checked lazy migration gate, and
returns a ready connection. The applied-state machinery — the runner-owned
`schema_version` bookkeeping table, `current_version`, and forward-only
`apply_pending` — lives in
[`stockroom.migrate`](../skills/sr-search/src/stockroom/migrate.py); migration
discovery (the ascending `NNNN_*.sql` list) lives in
[`stockroom.migrations`](../skills/sr-search/src/stockroom/migrations/__init__.py).
Cross-process safety is a two-layer lock: an `fcntl.flock` single-writer/
migrator token over DuckDB's own RW-exclusive file lock, with bounded reader
backoff that degrades to a typed `WarehouseBusyError` rather than blocking
forever. `schema_version` is runner-created and deliberately absent from
`0001`, so the locked product DDL and its golden snapshot stay untouched.

The Phase-2 milestone-1 upgrade is
[`0003_embeddings_hnsw_index.sql`](../skills/sr-search/src/stockroom/migrations/0003_embeddings_hnsw_index.sql):
it lands the deferred VSS/HNSW vector index — a cosine HNSW index over
`embeddings(vector)` with experimental persistence enabled (so deletes/inserts
work against the live index). It is *thin* — the index DDL only; it never
`INSTALL`s/`LOAD`s the `vss` extension. Loading is the chokepoint's job:
[`warehouse.ensure_vss(con)`](../skills/sr-search/src/stockroom/warehouse.py)
runs `LOAD vss` (install-on-missing) + the per-connection
`SET hnsw_enable_experimental_persistence` on **every** connection `open()`
returns (read-write *and* read-only — both verified to succeed on RO), so the
network `INSTALL` stays off the shipped DDL and the runtime read path. The
cumulative post-`0003` shape (columns + PKs **and** an `indexes` section — the
cosine metric is not introspectable via `duckdb_indexes()`, so it is verified
functionally) is pinned by
[`test_schema_0003.py`](../skills/sr-search/tests/test_schema_0003.py) against
[`0003_snapshot.json`](../skills/sr-search/tests/fixtures/schema/0003_snapshot.json);
`0001`/`0002` snapshots stay frozen. Schema-aware fixtures (`migrated_con`, the
real-chain runner tests) call `ensure_vss` before applying the chain.

The first real schema-changing, data-preserving upgrade is
[`0002_workspace_identity.sql`](../skills/sr-search/src/stockroom/migrations/0002_workspace_identity.sql):
it replaces the lossy `sessions.project_path` with two single-meaning columns —
`project_id` (the harness's encoded project-dir slug, stored *verbatim*: the
always-present grouping identity) and a re-semantic `cwd` (the real project-root
path, best-effort, `NULL` when unknown). It is structural (no backfill — the
verbatim slug is unrecoverable from the old lossy value, so pre-existing rows
carry `project_id = NULL` until a `--full` re-ingest). `0001` and its snapshot
stay frozen (forward-only); the cumulative post-`0002` shape is pinned by
[`test_schema_0002.py`](../skills/sr-search/tests/test_schema_0002.py) against
[`0002_snapshot.json`](../skills/sr-search/tests/fixtures/schema/0002_snapshot.json).
Schema-changing ingest/writer tests run against the `migrated_con` fixture (the
full chain via `apply_pending`); the frozen `0001` contract tests keep using
`schema_con`.

## Ingest (ETL)

The incremental, per-source-watermarked ETL that fills the schema from the
operator's own history lives in the
[`stockroom.ingest`](../skills/sr-search/src/stockroom/ingest/) package and runs
via `python -m stockroom.ingest [--full] [--harness cursor|claude]`. It is a
clean pipeline of single-responsibility modules: `model` (harness-neutral
`NormalizedSession`/`Message`/`ToolCall` records), the two clean-room parsers
`cursor` and `claude`, `sources` (discovery carrying the verbatim project-dir
slug as `project_id` + `_sync_state` watermark), `paths` (the `encode` transform
and `resolve_cwd` re-encode-and-match recovery), `enrich` (optional Cursor
`ai-code-tracking.db` model fill, a graceful no-op when absent), `writer`
(delete-then-insert by `(harness, session_id)` + watermark upsert), and the
`ingest()` orchestrator in `__init__`. Parsers depend only on `model` + stdlib
(pure, unit-testable); the writer is the only new DB writer and goes through
`warehouse.open(read_only=False)`. Workspace identity is honest: `project_id` is
the slug verbatim, while `cwd` is recovered from the records (Claude) or by
matching in-band transcript paths back to the slug (Cursor) and is `NULL` rather
than fabricated when nothing matches — an invariant locked corpus-wide by a
round-trip property test (`encode_for(harness, cwd) == project_id` whenever `cwd`
is non-NULL).

Discovery roots default to `~/.cursor/projects` / `~/.claude/projects`,
**overridable via `STOCKROOM_CURSOR_ROOT` / `STOCKROOM_CLAUDE_ROOT`** (mirroring
`STOCKROOM_HOME`); the optional enrichment DB path is `STOCKROOM_AI_TRACKING_DB`.
The whole reconstruction output is locked by a golden snapshot
[`tests/fixtures/ingest/expected_rows.json`](../skills/sr-search/tests/fixtures/ingest/expected_rows.json),
generated by the test's own query helper and asserted byte-for-byte — the
ingest-side analogue of the `0001` schema snapshot, so any parser drift is a
conscious, reviewed change. Native-format sample transcripts for the parsers
live under
[`tests/fixtures/transcripts/`](../skills/sr-search/tests/fixtures/transcripts/),
laid out as faithful per-harness roots.

## Query (`sr-query`)

The first user-facing read surface lives in
[`stockroom.query`](../skills/sr-search/src/stockroom/query.py) and runs via
`python -m stockroom.query "<SQL>"` (or `… -` to read the statement from stdin).
It is a single runnable module (no `__main__.py`, unlike the `ingest` *package*):
it opens the warehouse **read-only** through the same `warehouse.open()`
chokepoint, executes arbitrary SQL, and renders the result through the shared
[`stockroom.render`](../skills/sr-search/src/stockroom/render.py) layer in a
selectable `--format` (**`tsv`** default — header + tab-separated rows, no count
trailer; `json`; `table` for the human pretty-print). Each string field is
truncated at read time via the shared `stockroom.truncate` mechanism
(`--detail compact|snippet|full`, default `snippet`) so a wide `text` column
cannot flood the caller. Read-only is the contract — the warehouse is
rebuildable ETL output and this surface only interrogates it, so DuckDB rejects
writes through it; the lazy migration gate still runs (a reader behind the schema
head transparently becomes the migrator). Errors are surfaced as clean stderr
messages (invalid SQL → `query failed: …`; absent warehouse → a "run
`python -m stockroom.ingest` first" hint) with no traceback. The library entry
`run_query(sql, *, con=None)` mirrors the ingest `con`-injection shape so it is
unit-testable against an injected connection. The model-invocable wrapper skill
[`skills/sr-query/SKILL.md`](../skills/sr-query/SKILL.md) (Phase-2 milestone 4)
encodes the safe LLM-ergonomic use of this surface — routing, the engine-invocation
contract (note: external callers must set `PYTHONPATH=<engine>/src`, since the
engine is `package = false`), `--format`/`--detail` discipline, guardrails, and a
schema map; only the empirical per-harness invocation-form verification remains
Phase 5.

## Embeddings (`stockroom.embed`)

The Phase-2 milestone-1 embedding pipeline lives in
[`stockroom.embed`](../skills/sr-search/src/stockroom/embed.py) and runs via
`python -m stockroom.embed [--full]`. It reads message text through the
`warehouse.open(read_only=False)` chokepoint, splits long text into bounded
overlapping chunks (`chunk_text`, pure stdlib), encodes each chunk to a 384-dim
vector, and writes **one `embeddings` row per chunk** (`chunk_index = 0..N-1`) —
the lossless per-chunk storage grain (max-sim dedup-to-owner is deferred to m2).
m1 embeds **messages only** (`owner_table='messages'`, `owner_id=message_id`).

Incremental by default: `embed_pending` selects non-empty messages lacking an
`embeddings` row for the *current* model (so new content and a model change both
re-embed) and replaces a selected owner's prior vectors (the `embeddings` PK
excludes `embed_model`, so models can't coexist at the same `chunk_index`);
`--full` re-embeds everything. The "changed-content" half is caught by a
cascade-delete in [`stockroom.ingest.writer`](../skills/sr-search/src/stockroom/ingest/writer.py)
(re-ingesting a session drops its message embeddings).

The model is `BAAI/bge-small-en-v1.5` (384-dim, 512-token window, MIT, no
`trust_remote_code`), chosen by an empirical, cross-corpus known-item retrieval
benchmark ([`planning/spikes/embed-model-eval/`](../planning/spikes/embed-model-eval/)).
Torch testability follows the `con`-injection precedent: `embed_chunks` /
`embed_pending` / the CLI take an injected `Encoder` (the CLI via an
`encoder_factory`), so the pipeline is unit-tested torch-free against a
deterministic `FakeEncoder` (shared from `tests/conftest.py`); the only
torch-dependent surface, `BgeEncoder` (lazy-imports `sentence_transformers`), has
an `importorskip("torch")`-gated test that CI skips. `EMBED_MODEL`/`EMBED_DIM`
are module constants; `embed_model` is recorded per row so a model swap is
incremental.

## Semantic search (`stockroom.semantic`)

The Phase-2 milestone-2 read surface lives in
[`stockroom.semantic`](../skills/sr-search/src/stockroom/semantic.py) and runs
via `python -m stockroom.semantic "<query>" [-k N]`. Like `sr-query` it is a
single runnable module that opens the warehouse **read-only** through the
`warehouse.open()` chokepoint, with a `run_semantic_search(query, encoder, *,
con=None, limit=…, query_prefix=…)` library entry mirroring the `con`/encoder
injection shape (so it is unit-tested torch-free against the shared
`FakeEncoder`). It reuses `stockroom.embed`'s `Encoder` / `BgeEncoder` /
`EMBED_*` — no embedding logic is duplicated.

Flow: embed the query to a **single** vector (`embed_query`, never chunked) with
bge's asymmetric **query** instruction prefix (`QUERY_PREFIX`, the spike's
measured +0.037 MRR win; passages stay prefix-free); run a cosine KNN
(`array_cosine_distance`) over the `0003` HNSW index for the nearest
`limit * OVERFETCH` chunk rows; **dedup to the nearest chunk per owner** (the
max-sim grain m1 deferred — m1 stores one vector per chunk); join the top
`limit` owners back to their `messages` rows; and render the ranked results
through the shared `stockroom.render` layer in a selectable `--format` (default
`tsv`). `score` is cosine similarity (`1 - distance`) and the `preview`/`text`
field is run through the shared `stockroom.truncate` mechanism (`--detail`,
default `snippet`) — a *display* bound only, *not* the no-truncation violation:
full text stays whole in the store and in `SemanticHit.text`. The
real-model path is covered by one `importorskip("torch")`-gated end-to-end test.
The safe LLM wrapper, [`skills/sr-semantic/SKILL.md`](../skills/sr-semantic/SKILL.md)
(Phase-2 m5), is the single home for the surface's operational guidance (routing,
query phrasing, `-k`/`--format`/`--detail` discipline, guardrails); only the
empirical per-harness invocation-form verification remains Phase 5.

## Search entrypoint (`sr-search` skill)

The friendly-default search surface is prose, not Python:
[`skills/sr-search/SKILL.md`](../skills/sr-search/SKILL.md) (Phase-2 m6) is a
model-invocable judgement skill that routes a question to the `sr-query` /
`sr-semantic` wrapper skills (or both) and synthesizes one answer. There is no
`stockroom.search` module and the skill carries no engine-invocation contract —
delegation is by sibling skill name with a relative-path fallback (see
`systemPatterns.md` → search-surface architecture).

## CLI dispatcher (`python -m stockroom`)

The Phase-3 m1 single CLI entrypoint lives in
[`stockroom.__main__`](../skills/sr-search/src/stockroom/__main__.py):
`python -m stockroom <subcommand>` dispatches the first token to the existing
module CLIs (`query`, `semantic`, `ingest`, `embed`, `migrate`), forwarding
everything after it verbatim to that module's own `main(argv)` and returning
its exit code unchanged — modules keep sole ownership of their flags, so
`<subcommand> --help` is the module's own help. Top-level `--help` lists the
subcommands and `--version` prints `stockroom.__version__` (the m2 shim's
identity probe). Dispatch imports the target module lazily, keeping the
help/error paths free of heavy imports. `stockroom.migrate` gained its CLI
here (`python -m stockroom.migrate`): it migrates the warehouse to the schema
head through the `warehouse.open()` chokepoint (creating a missing warehouse —
the explicit schema bootstrap) and reports the resulting version. The on-path
`stockroom` shim that execs into this dispatcher is Phase-3 m2.

## Read-time truncation (`stockroom.truncate`)

The Phase-2 milestone-3 shared output-truncation mechanism lives in
[`stockroom.truncate`](../skills/sr-search/src/stockroom/truncate.py): a pure,
stdlib-only `truncate_cell(value, detail)` plus the `compact | snippet | full`
detail levels (`LEVEL_WIDTHS` `40 / 120 / None`, `DEFAULT_DETAIL = "snippet"`). It
collapses a cell to a single line and bounds it to the level's character budget,
appending a marker that reports the hidden character count (`…(+482)`); `full` is
the unbounded escape. The shared
[`stockroom.render`](../skills/sr-search/src/stockroom/render.py) layer consumes it
for both read surfaces in every `--format`; each CLI exposes the `--detail` flag
(alongside `--format`). Truncation is strictly read-time — full content stays whole
at rest and in the returned `QueryResult.rows` / `SemanticHit.text`. Unit-tested in
[`tests/test_truncate.py`](../skills/sr-search/tests/test_truncate.py); the
`sr-query` / `sr-semantic` wrapper skills (shipped in Phase-2 m4/m5) are the
single home for the operational advice on *when* to reach for each level.

## Output rendering (`stockroom.render`)

The Phase-2 milestone-3.5 presentation chokepoint
[`stockroom.render`](../skills/sr-search/src/stockroom/render.py) is the single
home for how the read surfaces print: `format_query(columns, rows, *, fmt, detail)`
and `format_semantic(hits, *, fmt, detail)` dispatch on `--format` —
**`tsv`** (default, header + tab-separated rows, no count trailer), `json`
(a single `{columns, rows}` / `{results: [...]}` object), or `table` (the
column-aligned human pretty-print, with the `(N rows)`/`(N results)` trailer). The
former private renderers `query._format_table` / `semantic._format_hits` were moved
here. `--detail` truncation is applied in every format via `stockroom.truncate`;
the library return types are unchanged (rendering is strictly the print boundary).
Decision record: [`planning/brainstorm/print-for-who.md`](../planning/brainstorm/print-for-who.md);
unit-tested in [`tests/test_render.py`](../skills/sr-search/tests/test_render.py).

## Testing Process

All work is **test-first** per the workspace TDD rule (`.cursor/rules/shared/always-tdd.mdc`); test-running discipline in `.cursor/rules/shared/test-running-practices.mdc`. Tests run under `pytest`, configured in [`skills/sr-search/pyproject.toml`](../skills/sr-search/pyproject.toml) (`[tool.pytest.ini_options]`). **Day-to-day:** `make test` / `make lint` / `make format` / `make ci` from the repo root ([`Makefile`](../Makefile)); lint/format is `ruff`, whole-tree licensing is `make reuse`. The full gate also runs in [`.github/workflows/ci.yml`](../.github/workflows/ci.yml).
