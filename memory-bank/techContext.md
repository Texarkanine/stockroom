# Tech Context

Stockroom is a local **Python** application managed end-to-end with **uv**, storing agentic-coding history in a single-file **DuckDB** warehouse with local **`sentence-transformers`** embeddings indexed via DuckDB's **VSS/HNSW** extension. It ships as a **dual-manifest** Cursor/Claude-Code plugin with **no build step** (committed layout = install layout).

**Authoritative source (until the end-of-roadmap cut): [`planning/tech-brief.md`](../planning/tech-brief.md).**

This file is intentionally thin right now and is designed to **accrete**. The tech brief is explicitly forward-looking; as each roadmap phase lands real configuration, this file gains pointers to those canonical artifacts (`pyproject.toml`, `uv.lock`, `release-please-config.json`, the migration SQL, the test config) and the brief's role correspondingly shrinks. **Cut gate:** at the end-of-roadmap distillation, this file must stand alone with zero references into `planning/`.

## Environment Setup

uv provisions the interpreter pinned by `requires-python`. Locked deps via `make sync` (or `uv sync --frozen --no-config` in `skills/sr-search/`); **regenerate the lock hermetically** with `make lock` (or `uv lock --no-config`) so ambient user config can't leak in. **Torch is the one exception** — held out of the lock and provisioned per-machine out of band. Never run an exact sync after installing it: the current root Makefile's sync prerequisite is still exact, so `make format` / `make ci` remove Torch and require restoring the confirmed wheel before production-path smoke testing; this is a known tooling debt until that prerequisite becomes inexact. Recipe proven in [`planning/spikes/o9-torch/`](../planning/spikes/o9-torch/); full detail in tech-brief → "The Torch Exception". The canonical project config is [`skills/sr-search/pyproject.toml`](../skills/sr-search/pyproject.toml) (the `requires-python` floor, the `[tool.uv] override-dependencies` torch marker, and `package = false`) with its hermetic [`skills/sr-search/uv.lock`](../skills/sr-search/uv.lock); the torch-safe run contract is documented in the [root README](../README.md).

## Build Tools

uv for dependency resolution (no compile/bundle/transpile step) and `release-please` for version syncing into both plugin manifests. Canonical config: [`skills/sr-search/pyproject.toml`](../skills/sr-search/pyproject.toml) + [`uv.lock`](../skills/sr-search/uv.lock), and [`release-please-config.json`](../release-please-config.json) + [`.release-please-manifest.json`](../.release-please-manifest.json) (writes `$.version` into both `plugin.json` manifests). CI is [`.github/workflows/ci.yml`](../.github/workflows/ci.yml); release automation is [`.github/workflows/release-please.yaml`](../.github/workflows/release-please.yaml). **Local iteration** is via the root [`Makefile`](../Makefile) (`make help` lists sync/lock/test/lint/format/reuse/ci targets; engine commands use `--no-config` and test/lint execution uses `--no-sync`, subject to the exact-sync prerequisite caveat above).

The dashboard front-end is a committed no-build surface: native ES modules in [`stockroom/dashboard/static/`](../skills/sr-search/src/stockroom/dashboard/static/) load the exact vendored Chart.js 4.5.1 UMD artifact locally, with no package manifest, npm install, bundler, transpiler, or runtime network dependency. Contributors and CI use Node 22 only to run the pure client/coordinator contracts through its stable built-in test runner (`make test-js`, which executes `node --test tests-js/*.test.mjs` from the engine directory).

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

The Phase-4 dashboard substrate upgrade is
[`0004_observation_times.sql`](../skills/sr-search/src/stockroom/migrations/0004_observation_times.sql):
`sessions.source_mtime` records source-transcript provenance and supplies an
honest last-activity fallback where a harness has no authored timestamps;
`messages.first_seen_at` records stockroom's first observation and is carried
forward by deterministic message identity across re-ingest. Existing rows stay
honestly NULL until observed; the cumulative shape is pinned by
[`test_schema_0004.py`](../skills/sr-search/tests/test_schema_0004.py) and
[`0004_snapshot.json`](../skills/sr-search/tests/fixtures/schema/0004_snapshot.json).

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
`ai-code-tracking.db` model fill from `ai_code_hashes` / `conversation_summaries`,
resolved via env override then conventional/`ai-tracking`/WSL-mount candidates;
graceful no-op when absent), `writer`
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
`stockroom ingest` first" hint, pinned exactly by the CLI tests) with no
traceback. The library entry
`run_query(sql, *, con=None)` mirrors the ingest `con`-injection shape so it is
unit-testable against an injected connection. The model-invocable wrapper skill
[`skills/sr-query/SKILL.md`](../skills/sr-query/SKILL.md) (Phase-2 milestone 4,
trimmed to the `stockroom query` contract in Phase-3 m5)
encodes the safe LLM-ergonomic use of this surface — routing,
`--format`/`--detail` discipline, guardrails, and a
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

## Dashboard metrics API (`stockroom.dashboard`)

The Phase-4 milestone-1 local dashboard backend lives in
[`stockroom.dashboard`](../skills/sr-search/src/stockroom/dashboard/): eight
JSON metric endpoints plus packaged static-file serving on a loopback-only
stdlib `ThreadingHTTPServer`. Each request opens its own read-only connection
through [`warehouse.open_current()`](../skills/sr-search/src/stockroom/warehouse.py),
which never migrates and turns missing, stale, or writer-busy warehouses into
actionable 503 responses. Window ownership stays in the metric functions
(`since` inclusive, `until` exclusive, endpoint-specific defaults); the HTTP
layer parses only supplied bounds. Overview exposes additive
`prev_distinct_projects` beside `distinct_projects` so the Projects KPI can
delta distinct-to-distinct without summing per-harness `prev_projects`.
`stockroom dashboard` (dispatcher → [`stockroom.dashboard.__main__`](../skills/sr-search/src/stockroom/dashboard/__main__.py)) provides the idempotent port-6767 probe and detached/foreground launcher; `python -m stockroom.dashboard` remains a direct equivalent. Contracts are pinned by the dashboard metrics, server, and CLI test modules. The thin wrapper skill is [`skills/sr-dashboard/SKILL.md`](../skills/sr-dashboard/SKILL.md).

The Phase-4 milestone-2 browser surface is the semantic single-pane [`static/index.html`](../skills/sr-search/src/stockroom/dashboard/static/index.html), a pure/tested transformation layer in [`dashboard-core.mjs`](../skills/sr-search/src/stockroom/dashboard/static/dashboard-core.mjs), injectable atomic request coordination in [`dashboard-data.mjs`](../skills/sr-search/src/stockroom/dashboard/static/dashboard-data.mjs), and an effects-only DOM/Chart.js adapter in [`dashboard.mjs`](../skills/sr-search/src/stockroom/dashboard/static/dashboard.mjs). Aggregate/Compare remains client-owned, wrapped remains all-time and unfiltered, harness keys remain open and positionally colored, and all warehouse-derived strings enter through safe text/attribute DOM APIs. Deterministic JavaScript behavior is covered under [`tests-js/`](../skills/sr-search/tests-js/); actual canvas rendering, native interaction, responsive layout, theme appearance, and offline-network verification remain an explicit real-browser QA boundary rather than a headless CI dependency.

## CLI dispatcher (`python -m stockroom`)

The Phase-3 m1 single CLI entrypoint lives in
[`stockroom.__main__`](../skills/sr-search/src/stockroom/__main__.py):
`python -m stockroom <subcommand>` dispatches the first token to the module
CLIs registered in `SUBCOMMANDS` (`query`, `semantic`, `ingest`, `embed`,
`migrate`, `shim`, `doctor`, `schedule`, `dashboard`), forwarding everything
after it verbatim to that module's own `main(argv)` and returning its exit
code unchanged — modules keep sole ownership of their flags, so
`<subcommand> --help` is the module's own help. Top-level `--help` lists the
subcommands and `--version` prints `stockroom.__version__` (the m2 shim's
identity probe). Dispatch imports the target module lazily, keeping the
help/error paths free of heavy imports. `stockroom.migrate` gained its CLI
here (`python -m stockroom.migrate`): it migrates the warehouse to the schema
head through the `warehouse.open()` chokepoint (creating a missing warehouse —
the explicit schema bootstrap) and reports the resulting version. The on-path
`stockroom` shim that execs into this dispatcher is the Phase-3 m2
`stockroom.shim` (see the next section).

## On-path shim (`stockroom.shim`)

The Phase-3 m2 on-path `stockroom` command is a generated POSIX-sh shim
(default `~/.local/bin/stockroom`) rendered from the in-package template
[`shim_template.sh`](../skills/sr-search/src/stockroom/shim_template.sh) by
[`stockroom.shim`](../skills/sr-search/src/stockroom/shim.py) (the dispatcher's
sixth subcommand: `stockroom shim install|rectify`). The shim is **baked-only
and succeed-or-refuse**: it checks `uv` (one-line error, exit 127), checks the
baked `APP_DIR/pyproject.toml` (one-line owner-appropriate remedy), then execs
the dispatcher through the torch-safe contract (`PYTHONPATH="$APP_DIR/src"
exec uv run --project "$APP_DIR" --no-sync --no-config python -m stockroom
"$@"`). It carries **no resolution logic** — never scans, ranks, or guesses.

All policy lives in the tested Python layer: ownership (a
`# STOCKROOM_OWNER=<cursor|claude|dev>` header marker; only the owner may
rewrite; takeover of a foreign shim requires a *dead* incumbent baked dir
*and* the explicit `--takeover` flag), atomic 0o755 writes, PATH-membership
reporting, and a conditional install-time `stockroom --version` verify.
Staleness healing is hook-driven: each harness's sessionStart hook
([`hooks/cursor-hooks.json`](../hooks/cursor-hooks.json) /
[`hooks/claude-hooks.json`](../hooks/claude-hooks.json), pointed to by the
`"hooks"` key in each plugin manifest) is one combined silenced command —
plugin-root bootstrap of `shim rectify --owner <harness> --app-dir
${*_PLUGIN_ROOT}/skills/sr-search`, then on-path `stockroom dashboard`
(port bind is the launch mutex). Failures are swallowed (`|| true`).
`rectify` rewrites only an owned, drifted shim and never creates one; it
cannot depend solely on the on-path shim (chicken-egg). Dev parity: `make
shim` installs with owner `dev` baking the checkout; harness hooks never
touch it. Decision records:
`memory-bank/active/creative/creative-shim-{staleness-resolution,generation-surface}.md`
(until archived).

## Environment diagnostics (`stockroom.doctor`)

The Phase-3 m3 read-only diagnostic surface lives in
[`stockroom.doctor`](../skills/sr-search/src/stockroom/doctor.py) (the
dispatcher's seventh subcommand) with two actions. `probe` reports torch-free
environment facts as aligned `key: value` lines — OS/arch (`platform`), GPU
name/driver/driver-CUDA ceiling/compute capability (`nvidia-smi` in its stable
`--query-gpu=` CSV mode; absence or any failure degrades to a reported fact,
never an error), torch import state, and the engine dir. It carries **no**
wheel-recommendation logic — facts only; the mapping is judgment in the
`sr-initialize` skill prose. `smoke` is the loud-failing verification: it
prints `torch.__version__` and `torch.cuda.is_available()`, encodes one string
through the production `BgeEncoder` path, and checks the vector width — exit 0
with an `ok` summary, or exit 1 with exactly one stderr line that always
carries the *next action* (the errmsg ratchet: torch-missing prints the
literal `uv pip install torch --no-config --index … --directory <engine>`
command — `--directory`, not `--project`, because `uv pip` only discovers the
venv via the working directory). Injection mirrors the engine convention
(`smi_runner`, `torch_importer`, `encoder_factory`), so everything but the one
`importorskip("torch")`-gated real-model test runs torch-free
([`test_doctor.py`](../skills/sr-search/tests/test_doctor.py) /
[`test_doctor_cli.py`](../skills/sr-search/tests/test_doctor_cli.py)).

## Nightly scheduling (`stockroom.schedule`)

The Phase-3 m4 scheduler-entry manager lives in
[`stockroom.schedule`](../skills/sr-search/src/stockroom/schedule.py) (the
dispatcher's eighth subcommand): `stockroom schedule {install|status|remove}
[--time HH:MM]` (default `03:30`) manages the nightly
`stockroom ingest && stockroom embed` job on the platform scheduler —
cron on Linux/WSL via a marker-delimited managed crontab block (foreign
lines pass through byte-for-byte; install strips-then-appends, so
re-install is idempotent by construction), launchd on macOS via an owned
`jp.ne.cani.stockroom.nightly.plist` (rewritten in place, reloaded
bootout-then-bootstrap with the not-loaded bootout failure tolerated).
Both halves render the *same* payload — a `%`-free
`(date; stockroom ingest && stockroom embed) >> <home>/logs/nightly.log 2>&1`
in a `/bin/sh -c` wrapper under an install-time-resolved absolute `PATH=`
(the shim's and uv's dirs via `shutil.which`), because the scheduler
environment is minimal (`PATH=/usr/bin:/bin`) and unredirected cron output
is mailed and discarded on MTA-less boxes. Entries invoke the shim by
name — never an engine path. Install refuses when the shim is not on
`PATH` (naming the fix), and warns — without failing — when no cron
daemon (`cron`/`crond`) is running. `status` is facts-only, exit 0
either way: the installed entry (or `not installed`), daemon liveness
(cron platforms), and the `log:` location. External effects run through
injectable seams (`crontab`/`launchctl` runners, `which`, the daemon
check, the agents dir) in
[`test_schedule.py`](../skills/sr-search/tests/test_schedule.py) /
[`test_schedule_cli.py`](../skills/sr-search/tests/test_schedule_cli.py).

## Onboarding (`sr-initialize` skill)

Machine onboarding is prose orchestration over tested units:
[`skills/sr-initialize/SKILL.md`](../skills/sr-initialize/SKILL.md) owns the
irreducible bootstrap (the uv check, plugin-root/sibling-relative engine-dir
resolution, and the **one legitimate exact sync** — `uv sync --frozen
--no-config`, guarded to run only before torch exists), the human-confirmed
torch wheel choice (probe facts → recommendation → explicit user confirmation;
a self-managed-torch branch states the requirement and lets the smoke test be
the gate), the documented out-of-band `uv pip install torch --no-config
--directory … --index <chosen>` line, and shim binding via `stockroom shim
install --owner <harness>` (dev checkouts defer to `make shim`). It is
idempotent with no progress file — the environment is the state; a re-run
re-probes and skips green steps. It carries the one sanctioned pre-shim
invocation incantation; everything after the shim lands is `stockroom
<subcommand>` — including the closing steps: nightly scheduling
(re-probe via `stockroom schedule status`, user consent + time-of-night,
`stockroom schedule install`, warnings relayed verbatim) and the first
full run (`stockroom ingest --full`, `stockroom embed`, a
`stockroom query` count sanity-check) that leaves the warehouse
populated, embedded, and query-ready.

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

All work is **test-first** per the workspace TDD rule (`.cursor/rules/shared/always-tdd.mdc`); test-running discipline in `.cursor/rules/shared/test-running-practices.mdc`. Python/static/HTTP contracts run under `pytest`, configured in [`skills/sr-search/pyproject.toml`](../skills/sr-search/pyproject.toml) (`[tool.pytest.ini_options]`), while deterministic dashboard JavaScript contracts run directly under Node 22's built-in runner from [`skills/sr-search/tests-js/`](../skills/sr-search/tests-js/) with no npm dependencies. **Day-to-day:** `make test` / `make test-js` / `make lint` / `make format` / `make ci` from the repo root ([`Makefile`](../Makefile)); lint/format is `ruff`, whole-tree licensing is `make reuse`. The full gate also runs in [`.github/workflows/ci.yml`](../.github/workflows/ci.yml).

## Design System

The dashboard's canonical visual and interaction authority is [`planning/brainstorm/Cross-harness Warehouse (standalone).html`](../planning/brainstorm/Cross-harness%20Warehouse%20(standalone).html), interpreted through the behavioral contract in [`planning/brainstorm/dashboard-spec.md`](../planning/brainstorm/dashboard-spec.md). Both are design guides rather than pixel law: shipped API semantics, accessibility, the offline/no-build constraint, and explicit scope decisions take precedence where they conflict.
