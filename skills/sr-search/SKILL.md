---
name: sr-search
description: Search your local warehouse of agentic-coding history. (Search behavior lands in Phase 2; this directory currently hosts the shared stockroom engine.)
license: "Multiple — see LICENSES/ and REUSE.toml"
enable-model-invocation: false
---

# sr-search

This directory is the home of the **shared stockroom engine** — the locked,
torch-free uv project (`pyproject.toml`, `uv.lock`, `src/stockroom/`, `tests/`)
that every other `sr-*` skill invokes. It lives inside `sr-search` because
search is stockroom's core entrypoint.

## Status: engine landing, search not yet wired

This is an honest placeholder for the *search skill*, not a dummy. The shared
engine has grown through Phase 1 (the DuckDB warehouse, migrations, ingest, and
`sr-query`) and Phase 2 milestones 1 (the **embedding pipeline**) and 2
(**`sr-semantic`** pure vector search).

What exists today as runnable engine entrypoints:

- `python -m stockroom.ingest [--full]` — fill the warehouse from local Cursor /
  Claude Code history.
- `python -m stockroom.query "<SQL>"` — read-only SQL over the warehouse.
- `python -m stockroom.embed [--full]` — embed message text into the
  `embeddings` table (per-chunk `FLOAT[384]` vectors via a local
  `sentence-transformers` model, behind the DuckDB VSS/HNSW cosine index;
  incremental by default).
- `python -m stockroom.semantic "<query>" [-k N]` — read-only **pure vector
  search**: embeds the query (with the bge query prefix), runs cosine KNN over
  the HNSW index, dedups to one row per owner message, and prints a ranked,
  similarity-scored table.

The headline **blended keyword + semantic search** with context-aware read-time
truncation — the behavior this skill is ultimately named for — lands in Phase 2
milestone 3 (`sr-search`). Until then, this skill itself performs no action.

## How sibling skills will use the engine

The engine is invoked through the plugin-root-relative resolution contract
(resolved once on startup) and the torch-safe run contract (never an exact
sync), both documented in `memory-bank/systemPatterns.md`:

```bash
APP_DIR="${CURSOR_PLUGIN_ROOT:+$CURSOR_PLUGIN_ROOT/skills/sr-search}"
if [ -z "$APP_DIR" ] || [ ! -d "$APP_DIR" ]; then
  APP_DIR="$(dirname "$(find -L ~/.cursor/plugins -path '*/stockroom/*/skills/sr-search/pyproject.toml' 2>/dev/null | head -1)")"
fi
uv run --project "$APP_DIR" --no-sync python -m stockroom.<entrypoint> ...
```
