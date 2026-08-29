# Tech Context

Stockroom is a local **Python** application managed with **uv**, storing agentic-coding history in a single-file **DuckDB** warehouse with local **`sentence-transformers`** embeddings indexed via DuckDB **VSS/HNSW**. It ships as a **dual-manifest** Cursor/Claude Code plugin with **no build step** (committed layout = install layout). The engine lives in [`skills/sr-search/`](../skills/sr-search/).

## Environment Setup

uv provisions the interpreter pinned by `requires-python` in [`skills/sr-search/pyproject.toml`](../skills/sr-search/pyproject.toml). Locked deps via `make sync` (or `uv sync --frozen --no-config` in the engine dir). Regenerate the lock hermetically with `make lock` (`uv lock --no-config`). Torch is held out of the lock and provisioned per-machine; after smoke (or `make torch`), a hashed freeze is written under stockroom home and heal replays it with `--require-hashes` (see [`docs/user-guide/troubleshooting/torch.md`](../docs/user-guide/troubleshooting/torch.md)). After torch is installed, never run an exact sync — use `--no-sync` / `--inexact`. Day-to-day engine / Torch / docs / dashboard / skills loops and Make targets: [`docs/contributing/iteration/index.md`](../docs/contributing/iteration/index.md). Enter / verify / exit localdev (atoms + recipe): [`docs/contributing/preparation.md`](../docs/contributing/preparation.md). Human docs site: root stub [`pyproject.toml`](../pyproject.toml) + [`properdocs.yaml`](../properdocs.yaml) (`make docs` / `make docs-build`).

Warehouse home: `$XDG_DATA_HOME/stockroom` or `~/.local/share/stockroom`, overridable via `STOCKROOM_HOME`. Optional settings: `$XDG_CONFIG_HOME/stockroom/config.toml` (default `~/.config/stockroom/config.toml`). Ingest roots: `STOCKROOM_CURSOR_ROOT` / `STOCKROOM_CURSOR_CHATS_ROOT` / `STOCKROOM_CLAUDE_ROOT`. Cursor model enrich: walk/merge all `ai-code-tracking.db` candidates (+ optional `[cursor].ai_tracking_dbs`); `STOCKROOM_AI_TRACKING_DB` forces a single DB.

## Build Tools

- **uv** — dependency resolution; canonical engine config [`skills/sr-search/pyproject.toml`](../skills/sr-search/pyproject.toml) + [`uv.lock`](../skills/sr-search/uv.lock) (`package = false`, torch override-dependencies). Root stub [`pyproject.toml`](../pyproject.toml) + [`uv.lock`](../uv.lock) is docs-only (`uv sync --group docs`).
- **properdocs** — human doc site over [`docs/`](../docs/); config [`properdocs.yaml`](../properdocs.yaml); `make docs` / `make docs-build`.
- **release-please** — [`release-please-config.json`](../release-please-config.json) + [`.release-please-manifest.json`](../.release-please-manifest.json); syncs version into both plugin manifests.
- **Makefile** — root [`Makefile`](../Makefile) for sync/lock/test/coverage/lint/format/reuse/ci/torch/shim/docs plus contributor localdev atoms (`local-skills`, `local-engine`, `local-dashboard`, composer `localdev`, `localdev-clean`, `localdev-status`; harness-scoped targets require `HARNESS=cursor|claude`; `shim` with optional `TAKEOVER=1` / `FORCE=1`). Fat localdev shell lives in [`scripts/localdev.sh`](../scripts/localdev.sh) (POSIX); Make orchestrates.
- **CI / release** — [`.github/workflows/ci.yaml`](../.github/workflows/ci.yaml) (engine gate + Codecov uploads), [`.github/workflows/docs.yaml`](../.github/workflows/docs.yaml), [`.github/workflows/pr-title.yaml`](../.github/workflows/pr-title.yaml) (conventional-commit PR titles), [`.github/workflows/release-please.yaml`](../.github/workflows/release-please.yaml). Coverage flags/paths in root [`codecov.yml`](../codecov.yml). Dependency version updates: [`.github/dependabot.yaml`](../.github/dependabot.yaml) (UV docs + engine, GitHub Actions).
- **Dashboard front-end** — committed native ES modules under [`stockroom/dashboard/static/`](../skills/sr-search/src/stockroom/dashboard/static/) with vendored Chart.js and markdown-it; no npm install or bundler. Node 22 runs `make test-dashboard-js` / `make coverage-dashboard-js`.


## Warehouse Schema

Authoritative DDL is the migration chain under [`skills/sr-search/src/stockroom/migrations/`](../skills/sr-search/src/stockroom/migrations/). Schema-contract tests and golden snapshots live under [`skills/sr-search/tests/`](../skills/sr-search/tests/) and `tests/fixtures/schema/`. Logical ERD edges are `-- @rel` / `-- @rel-none` comments in those migrations; regenerate the query-facing picture with `make schema-docs` (SSOT [`skills/sr-query/references/warehouse-schema.md`](../skills/sr-query/references/warehouse-schema.md), Advanced symlink [`docs/advanced/warehouse-schema.md`](../docs/advanced/warehouse-schema.md)). Consumers use [`stockroom.warehouse.open()`](../skills/sr-search/src/stockroom/warehouse.py); migration bookkeeping is [`stockroom.migrate`](../skills/sr-search/src/stockroom/migrate.py). VSS is loaded at the warehouse chokepoint (`ensure_vss`); the HNSW index is migration `0003`.

## Engine Surfaces

| Surface | Module / skill | Role |
| --- | --- | --- |
| Ingest | `stockroom.ingest` | ETL from Cursor + Claude Code |
| Backfill | `stockroom.backfill` | One-shot legacy-store excavation; human-run, never scheduled |
| Query | `stockroom.query` / `sr-query` | Read-only SQL |
| Embed | `stockroom.embed` | Local vectors |
| Semantic | `stockroom.semantic` / `sr-semantic` | Vector search |
| Search | `sr-search` | Judgement router (no Python fusion module) |
| Dashboard | `stockroom.dashboard` / `sr-dashboard` | Local metrics UI on port 58008 |
| CLI | `python -m stockroom` / on-path shim | Subcommand dispatcher |
| Doctor | `stockroom.doctor` | Environment probe + torch smoke |
| Schedule | `stockroom.schedule` | Nightly cron / launchd |
| Initialize | `sr-initialize` | Machine onboarding |

Shared presentation: [`stockroom.render`](../skills/sr-search/src/stockroom/render.py) + [`stockroom.truncate`](../skills/sr-search/src/stockroom/truncate.py). Hooks: [`hooks/cursor-hooks.json`](../hooks/cursor-hooks.json), [`hooks/claude-hooks.json`](../hooks/claude-hooks.json).

## Testing Process

Test-first per `.cursor/rules/shared/always-tdd.mdc`; run discipline in `.cursor/rules/shared/test-running-practices.mdc`. Python contracts: `pytest` + `pytest-xdist` configured in [`skills/sr-search/pyproject.toml`](../skills/sr-search/pyproject.toml) (`addopts = ["-n", "auto"]`; override with `-n0` for serial). Coverage is opt-in via `make coverage-engine` (`pytest-cov` → lcov) and `make coverage-dashboard-js` (Node `--experimental-test-coverage` → lcov); CI uploads both with Codecov flags (`engine`, `dashboard-js`) per [`codecov.yml`](../codecov.yml). Dashboard JS: Node 22 built-in runner via `make test-dashboard-js`; dashboard Python slice via `make test-dashboard-py` (no sync). Day-to-day: `make test` / `make lint` / `make format` / `make reuse` / `make ci` from repo root. Lint/format is `ruff`.

## Design System

Dashboard UI authority is the shipped static surface: [`skills/sr-search/src/stockroom/dashboard/static/`](../skills/sr-search/src/stockroom/dashboard/static/) (`index.html`, `dashboard-core.mjs`, `dashboard-data.mjs`, `dashboard-session.mjs`, `dashboard-tokens.mjs`, `dashboard.mjs`, vendored Chart.js + markdown-it). Offline, no CDN; Aggregate/Compare and presentation policy live in the browser layer. SPA views use query-param deep links: metrics (default), sessions list (`?view=sessions&…`), and session view (`?view=session&harness=&session=`) — overview card (session metrics + tool/skill composition doughnuts) above a messages card (toolbar, title, turns); optional `#msg-{ordinal}` scrolls to that turn after async load (top of bubble); `#msg-{ordinal}-sa-{n}` scrolls to a spawned-subagent pill. Session detail API exposes optional `tokens` from VIEW `session_token_usage`, plus session-scoped `tools` / `skills` aggregates shaped like the metrics endpoints for Chart.js reuse. Browser history is the only back navigation between views. API semantics and accessibility constraints in the dashboard package take precedence over any external mockups.

Docs site chrome (not product UI): ProperDocs / Material tokens live in [`docs/stylesheets/extra.css`](../docs/stylesheets/extra.css), wired from [`properdocs.yaml`](../properdocs.yaml) (`primary`/`accent: custom` + `extra_css`). Warm paper light / ember dark — Texarkanine paper/ember tokens.
