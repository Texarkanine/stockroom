# CLI

The on-path `stockroom` command is the torch-safe entrypoint to the engine. After initialize it usually lives at `~/.local/bin/stockroom` (or wherever your user bin is on `PATH`). Use it when you want the same engine the skills call — without an agent turn.

## Prerequisites

- A completed `sr-initialize` so the shim is installed and on `PATH`
- Familiarity with the agent path when you want it back: [Skill index](../user-guide/skills.md)

```bash
which stockroom
stockroom --help
```

If `stockroom` is missing, heal via `sr-initialize` — do not invent a clone-based `uv` bootstrap from this page.

## Invocation

Skills (`sr-query`, `sr-semantic`, …) orchestrate inside a harness. Out-of-band, you call the shim directly:

```bash
stockroom <subcommand> [flags…]
stockroom <subcommand> --help
```

The shim owns the torch-safe run contract and dispatches into the engine. Prefer it over calling the engine with bare `uv` as an end user.

## Read surfaces

These are the Advanced-owned depth for terminal use:

```bash
stockroom query "SELECT DISTINCT harness FROM sessions"
stockroom query --format table --detail full "SELECT message_id, role FROM messages LIMIT 5"
stockroom semantic "flaky dashboard tests" -k 10
```

| Subcommand | Role |
| --- | --- |
| `query` | Read-only SQL against the warehouse |
| `semantic` | Vector (semantic) search |

For schema and search mental model, see [Search](../user-guide/search.md) and [Architecture → Warehouse](../architecture/warehouse.md) / [Embeddings](../architecture/embeddings.md). This page does not fork skill flag tables — use `--help` and the skill `SKILL.md` files for operational recovery detail.

## Output shape

`query` and `semantic` share read-time presentation flags:

- `--format {tsv,json,table}` — default `tsv` (stream-friendly)
- `--detail {compact,snippet,full,raw}` — default `snippet`; truncation is display-only. Prefer `--format json --detail raw` when exact whitespace must match storage.

Full flag semantics: `stockroom query --help` / `stockroom semantic --help`.

## Environment overrides

Default stockroom home is `$XDG_DATA_HOME/stockroom` or `~/.local/share/stockroom`, overridable with `STOCKROOM_HOME`. Path topology (warehouse file, torch freeze, logs) is owned by [Installed layout](../user-guide/installed-layout.md) — do not re-derive filenames here.

Optional ingest-root overrides when your transcripts are not in the default places:

- `STOCKROOM_CURSOR_ROOT`
- `STOCKROOM_CLAUDE_ROOT`
- `STOCKROOM_AI_TRACKING_DB`

Catch-up ingest/embed recipes stay in [Load the Warehouse](../user-guide/ingest.md).

## Other subcommands

Ingest, embed, dashboard, doctor, schedule, migrate, shim, and torch exist on the same binary. Advanced does not deep-dive them:

| Need | Go here |
| --- | --- |
| Catch-up ingest / embed | [Load the Warehouse](../user-guide/ingest.md) |
| Metrics UI | [Dashboard](../user-guide/dashboard.md) |
| Torch / PATH / heal | [Troubleshooting](../user-guide/troubleshooting/index.md) · `sr-initialize` |
| Flag / recovery tables | each skill’s `SKILL.md`, or `stockroom <subcommand> --help` |

## See also

- [DuckDB](duckdb.md) — raw DuckDB CLI when you need SQL outside the presentation layer
- [Architecture](../architecture/index.md) — why the shim and read chokepoint exist
