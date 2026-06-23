# Tech Context

Stockroom is a local **Python** application managed end-to-end with **uv**, storing agentic-coding history in a single-file **DuckDB** warehouse with local **`sentence-transformers`** embeddings indexed via DuckDB's **VSS/HNSW** extension. It ships as a **dual-manifest** Cursor/Claude-Code plugin with **no build step** (committed layout = install layout).

**Authoritative source (until the end-of-roadmap cut): [`planning/tech-brief.md`](../planning/tech-brief.md).**

This file is intentionally thin right now and is designed to **accrete**. The tech brief is explicitly forward-looking; as each roadmap phase lands real configuration, this file gains pointers to those canonical artifacts (`pyproject.toml`, `uv.lock`, `release-please-config.json`, the migration SQL, the test config) and the brief's role correspondingly shrinks. **Cut gate:** at the end-of-roadmap distillation, this file must stand alone with zero references into `planning/`.

## Environment Setup

uv provisions the interpreter pinned by `requires-python`. Locked deps via `uv sync --frozen`; **regenerate the lock hermetically** with `uv lock --no-config` so ambient user config can't leak in. **Torch is the one exception** — held out of the lock, provisioned per-machine out of band, and preserved across syncs (never run an exact sync after installing it). Recipe proven in [`planning/spikes/o9-torch/`](../planning/spikes/o9-torch/); full detail in tech-brief → "The Torch Exception". The canonical project config is [`skills/sr-search/pyproject.toml`](../skills/sr-search/pyproject.toml) (the `requires-python` floor, the `[tool.uv] override-dependencies` torch marker, and `package = false`) with its hermetic [`skills/sr-search/uv.lock`](../skills/sr-search/uv.lock); the torch-safe run contract is documented in the [root README](../README.md).

## Build Tools

uv for dependency resolution (no compile/bundle/transpile step) and `release-please` for version syncing into both plugin manifests. Canonical config: [`skills/sr-search/pyproject.toml`](../skills/sr-search/pyproject.toml) + [`uv.lock`](../skills/sr-search/uv.lock), and [`release-please-config.json`](../release-please-config.json) + [`.release-please-manifest.json`](../.release-please-manifest.json) (writes `$.version` into both `plugin.json` manifests). CI is [`.github/workflows/ci.yml`](../.github/workflows/ci.yml); release automation is [`.github/workflows/release-please.yaml`](../.github/workflows/release-please.yaml).

## Testing Process

All work is **test-first** per the workspace TDD rule (`.cursor/rules/shared/always-tdd.mdc`); test-running discipline in `.cursor/rules/shared/test-running-practices.mdc`. Tests run under `pytest`, configured in [`skills/sr-search/pyproject.toml`](../skills/sr-search/pyproject.toml) (`[tool.pytest.ini_options]`), invoked torch-safely as `uv run --no-sync pytest` from `skills/sr-search/`. Lint/format is `ruff` (same pyproject); whole-tree licensing is checked with `reuse lint`. The full gate runs in [`.github/workflows/ci.yml`](../.github/workflows/ci.yml).
