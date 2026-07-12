# Advanced usage

Operate Stockroom **after** `sr-initialize` without another agent turn: the on-path `stockroom` shim and, when useful, the DuckDB CLI against the warehouse file.

This is an escape hatch for power users — not a second onboarding track. Bootstrap and heal still belong to `sr-initialize`. Do not use `make` / `uv` from a git clone as an end-user substitute for initialize.

## What you need

- A completed first-time setup (`stockroom` on `PATH`)
- Familiarity with [Using skills](../user-guide/using-skills.md) for the agent path when you want it back

## Surfaces

- [CLI](cli.md) — `stockroom query`, `semantic`, and related subcommands; optional raw DuckDB
