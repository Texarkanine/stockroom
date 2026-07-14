# CLI

The on-path `stockroom` command is the torch-safe entrypoint to the engine. After initialization it usually lives at `~/.local/bin/stockroom` (or wherever your user bin is on `PATH`). Use it when you want the same engine the skills call — without an agent turn.

## Prerequisites

- A completed `sr-initialize` so the shim is installed and on `PATH`
- Familiarity with the agent path when you want it back: [Skill index](../user-guide/skills.md)

```bash
which stockroom
stockroom --help
```

If `stockroom` is missing or the shim refuses, recover under [Troubleshooting → Installed layout](../user-guide/troubleshooting/index.md#installed-layout) — do not invent a clone-based `uv` bootstrap from this page.

## Invocation

Skills (`sr-query`, `sr-semantic`, …) orchestrate inside a harness. Out-of-band, you call the shim directly:

```bash
stockroom <subcommand> [flags…]
stockroom <subcommand> --help
```

The shim owns the torch-safe run contract and dispatches into the engine. Prefer it over calling the engine with bare `uv` as an end user.

## Read surfaces

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

!!! tip "The Default was for Agents"

	Semantic search just outputs data - nothing that works as a foreign key into other rows or an SQL query, *except* with `--format json`.

	Additionally, their output is truncated.

`stockroom semantic` was designed for agents to cast a wide net and find something promising, which they'd then do a fuller-detail JSON dump on. For you as a human (who doesn't care about the "context window" of your terminal), you probably always want to use

```bash
stockroom semantic --format json --detail raw "my query..."
```

instead of the default.

## See also

- [DuckDB](duckdb.md) — raw DuckDB CLI when you need SQL outside the presentation layer
- [Architecture](../architecture/index.md) — why the shim and read chokepoint exist
- Missing / broken shim: [Troubleshooting → Installed layout](../user-guide/troubleshooting/index.md#installed-layout)
