# Advanced usage

Escape hatches for power users who already finished `sr-initialize` and want to operate Stockroom from a terminal — without another agent turn.

## Audience

You have `stockroom` on `PATH`, a warehouse under stockroom home, and a reason to go outside the normal [User Guide](../user-guide/index.md) path. If you are still bootstrapping or healing a broken install, stay on `sr-initialize` and the User Guide — Advanced is not a second onboarding track.

## What Advanced is

Focused recipes for two confirmed usages:

- Running the on-path `stockroom` CLI yourself (query, semantic, and how that differs from `sr-*` skills)
- Opening the warehouse with the DuckDB CLI in read-only mode when you need ad-hoc SQL outside `stockroom query`

## What Advanced is not

- Not bootstrap or heal — that remains `sr-initialize` / User Guide troubleshooting
- Not a second User Guide — catch-up ingest/embed, dashboard, and torch remedies stay in the User Guide
- Not contributor localdev — checkout `make` / `uv` loops live in [Contributing](../contributing/index.md); do not use a git clone as an end-user substitute for initialize
- Not the systems atlas — for how pieces fit and which constraints not to remove, see [Architecture](../architecture/index.md)

## Surfaces

| Page | Escape hatch |
| --- | --- |
| [CLI](cli.md) | Out-of-band `stockroom` invocation and read surfaces |
| [DuckDB](duckdb.md) | Raw DuckDB CLI against the warehouse (read-only) |

## Related

- [User Guide](../user-guide/index.md) — product how-to after initialize
- [Architecture](../architecture/index.md) — systems atlas
- [Contributing](../contributing/index.md) — checkout iteration loops
