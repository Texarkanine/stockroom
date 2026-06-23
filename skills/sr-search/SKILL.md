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

## Status: skeleton (Phase 0)

This is an honest placeholder, not a dummy. Phase 0 ("Foundations") ships the
engine, the dual-manifest plugin scaffold, the hermetic lock, release-please
versioning, and the test/lint/format harness. **No product behavior ships yet.**

The actual semantic-search behavior — querying the DuckDB warehouse and
returning read-time-truncated results — is built in **Phase 2**. Until then,
this skill performs no action.

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
