# System Patterns

## How This System Works

Stockroom is a dual-manifest Cursor/Claude Code plugin whose Python engine lives inside `skills/sr-search/` as a locked, run-in-place `uv` project (`[tool.uv] package = false`). Everything is pinned through a committed `uv.lock` except torch, which is provisioned per-machine out of band. The warehouse is a single-file DuckDB database under a harness-neutral XDG home (`$XDG_DATA_HOME/stockroom` or `~/.local/share/stockroom`, overridable via `STOCKROOM_HOME`). Faithful capture is the product reason: kept fields are stored whole; truncation exists only at read time. Ingest is ETL into a harness-labeled schema (shared tables, a `harness` column per row): full prompts and responses land in `messages`, tool inputs are stored whole in `tool_calls.tool_input`, and only `tool_result` outputs are dropped — no raw mirror layer. Every consumer reaches DuckDB through `stockroom.warehouse.open()` (or the non-migrating `open_current()` for the dashboard). The on-path `stockroom` shim owns the entire invocation contract; wrapper skills say only `stockroom <subcommand>`. The session-start hook launches the dashboard and rectifies the shim — never ingests, never migrates, never errors.

## Locked uv project, torch held out of the lock

Lock hermetically with `uv lock --no-config`. Exclude torch via an impossible environment-marker override in `skills/sr-search/pyproject.toml` so it never enters the lock, then provision it per-machine (`uv pip install torch --no-config --index <wheel-url>`), smoke-test, and freeze the accepted stack under stockroom home. After torch is installed, never run an exact sync — use `uv run --no-sync` or `--inexact`. Local iteration is via the root [`Makefile`](../Makefile). See [`docs/torch.md`](../docs/torch.md).

## No truncation at rest; truncation is a read-time feature

Kept content is stored in full. Output truncation is applied only at read time by [`stockroom.truncate`](../skills/sr-search/src/stockroom/truncate.py) through [`stockroom.render`](../skills/sr-search/src/stockroom/render.py) (`--detail compact|snippet|full`). Full content stays whole in the warehouse and in returned data objects; over-budget cells are elided with a hidden-character marker.

## Harness-labeled schema, one meaning per field

One shared set of tables (`sessions`, `messages`, `tool_calls`, `embeddings`, `_sync_state`); every row carries `harness`. Columns mean one thing independent of harness — extraction may differ, meaning must not. Identity is uniform (`message_id = {session_id}#{ordinal}`); native ids are provenance (`source_*`), never join keys. Typed columns for queryable metrics; JSON only for irreducible heterogeneity (`tool_calls.tool_input`). Thinking/reasoning blocks are not stored when the harness separates them.

## Dual-manifest plugin; engine inside `sr-search`

`.cursor-plugin/plugin.json` and `.claude-plugin/plugin.json` over a shared `skills/` tree; committed layout equals install layout. release-please syncs version into both manifests. The full engine (`pyproject.toml`, `uv.lock`, `src/stockroom/`, migrations, tests) lives under `skills/sr-search/`.

Harness hooks are **not** the same JSON shape or event: Cursor native hooks (`hooks/cursor-hooks.json`) use flat `{ "version": 1, "hooks": { "sessionStart": [{ "command": "..." }] } }` per [Cursor Hooks](https://cursor.com/docs/hooks); Claude Code hooks (`hooks/claude-hooks.json`) keep nested `SessionStart` / `hooks[]` / `type: "command"`. Do not copy Claude structure into the Cursor file. Both harnesses bootstrap rectify with `uv python find --project … --no-config` (not bare `python3`, not `uv run --no-sync`). Cursor plugin hooks also require **Include third-party Plugins, Skills, and other configs** until [plugin hooks not loading](https://forum.cursor.com/t/plugin-hooks-not-loading-into-cursor-ide/156702) is fixed.

## The shim owns the invocation contract

The generated on-path shim (`~/.local/bin/stockroom`, from [`stockroom.shim`](../skills/sr-search/src/stockroom/shim.py)) owns engine-dir resolution, `PYTHONPATH`, and torch-safe uv flags. Wrapper skills carry no fallback incantation — missing `stockroom` on PATH means run `sr-initialize`. Regression-pinned by [`tests/test_skill_hygiene.py`](../skills/sr-search/tests/test_skill_hygiene.py). System-model rationale: [`skills/sr-search/references/system-model.md`](../skills/sr-search/references/system-model.md).

## Two-layer warehouse lock behind chokepoints

[`warehouse.open()`](../skills/sr-search/src/stockroom/warehouse.py) owns path resolution, lazy migration, and VSS load. Coordination uses `fcntl.flock` on a sidecar lock file; data integrity uses DuckDB's own file lock. Readers open read-only and back off to `WarehouseBusyError`. `open_current()` is the dashboard exception: read-only, no migrate, typed stale/busy errors. Migrations are numbered SQL under `src/stockroom/migrations/`; `schema_version` is runner-owned.

## Embeddings and semantic search

[`stockroom.embed`](../skills/sr-search/src/stockroom/embed.py) writes one vector per chunk (`BAAI/bge-small-en-v1.5`, 384-dim) through a read-write `open()`. [`stockroom.semantic`](../skills/sr-search/src/stockroom/semantic.py) does index KNN, over-fetch, max-sim owner dedup, with an asymmetric query prefix. Scores are relative within one query.

## Search-surface architecture: engine power, wrapper skills, judgement router

Python modules are raw surfaces; each `sr-*` skill holds LLM-safe usage. [`sr-search`](../skills/sr-search/SKILL.md) is a pure judgement router over `sr-query` / `sr-semantic` — no `stockroom.search` fusion module. The same split applies to onboarding (`stockroom.doctor` facts vs `sr-initialize` judgement) and scheduling (`stockroom.schedule` mechanism vs skill consent).

## Rendered-out artifacts: one tested owner each

Shim, harness hooks (`hooks/*.json`), and nightly scheduler entries each have one owner module and structural idempotency. No rendered artifact carries a raw engine path — scheduler entries invoke the shim by name.

## Read output through one chokepoint

Both read surfaces print only through [`stockroom.render`](../skills/sr-search/src/stockroom/render.py). Default `--format` is `tsv`; `json` and `table` are opt-in. `--detail` is orthogonal.

## Ingest: per-harness parsers, harness-neutral model

[`stockroom.ingest`](../skills/sr-search/src/stockroom/ingest/) parsers emit shared dataclasses; the writer is the only SQL touchpoint. Golden snapshot [`tests/fixtures/ingest/expected_rows.json`](../skills/sr-search/tests/fixtures/ingest/expected_rows.json) locks reconstruction. The warehouse outlives its sources: rows whose transcripts vanish are never pruned; observation-time fields (`messages.first_seen_at`) are not rebuildable from sources alone.

## Workspace identity: verify-don't-invert

`sessions.project_id` is the harness slug verbatim; `sessions.cwd` is best-effort real path, NULL when unknown. Candidates are accepted only when `encode_for(harness, candidate) == slug` ([`stockroom.ingest.paths`](../skills/sr-search/src/stockroom/ingest/paths.py)).

## Baked-only succeed-or-refuse shim

The shim has a baked engine dir and zero resolution logic — succeed correctly or refuse with a one-line remedy (including when the engine env cannot import locked deps). Session-start hooks run `shim rectify`, which re-bakes owned shims after plugin updates **and** ensures the engine uv env via torch-safe inexact sync plus torch reinstall from the hashed freeze at `{stockroom_home}/torch-requirements.txt` (`stockroom.torch_source`); `make shim` installs owner `dev` for checkouts. `make torch` / `sr-initialize` / `stockroom torch freeze` write that freeze (plus a `torch-index` sidecar).

## Layered licensing

Root [`REUSE.toml`](../REUSE.toml): AGPL on code; PPL-S layered on prompt-shaped skill content; code-shaped paths under `skills/**` re-asserted AGPL. Enforced by `reuse lint`.
