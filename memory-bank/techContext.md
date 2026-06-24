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
The migration framework that applies this SQL (version record, lazy gate,
exclusive write lock) lands in milestone 2.

## Testing Process

All work is **test-first** per the workspace TDD rule (`.cursor/rules/shared/always-tdd.mdc`); test-running discipline in `.cursor/rules/shared/test-running-practices.mdc`. Tests run under `pytest`, configured in [`skills/sr-search/pyproject.toml`](../skills/sr-search/pyproject.toml) (`[tool.pytest.ini_options]`). **Day-to-day:** `make test` / `make lint` / `make format` / `make ci` from the repo root ([`Makefile`](../Makefile)); lint/format is `ruff`, whole-tree licensing is `make reuse`. The full gate also runs in [`.github/workflows/ci.yml`](../.github/workflows/ci.yml).
