# CLI

The on-path `stockroom` command (`~/.local/bin/stockroom` after initialize) owns the torch-safe run contract and dispatches to engine subcommands.

```bash
stockroom --help
stockroom <subcommand> --help
```

## Common subcommands

| Subcommand | Role |
| --- | --- |
| `query` | Read-only SQL against the warehouse |
| `semantic` | Vector (semantic) search |
| `ingest` | Ingest harness history |
| `embed` | Embed pending message text |
| `doctor` | Environment facts / torch smoke |
| `dashboard` | Launch the local metrics UI |
| `schedule` | Nightly ingest+embed scheduler entry |
| `shim` / `torch` / `migrate` | Heal, freeze, and schema — prefer `sr-initialize` unless you know you need them |

Examples:

```bash
stockroom query "SELECT DISTINCT harness FROM sessions"
stockroom query --format table --detail full "SELECT message_id, role FROM messages LIMIT 5"
stockroom semantic "flaky dashboard tests" -k 10
stockroom ingest --full --verbose
stockroom embed --verbose
stockroom dashboard
```

### Output shape

`query` and `semantic` share read-time presentation flags:

- `--format {tsv,json,table}` — default `tsv` (stream-friendly)
- `--detail {compact,snippet,full,raw}` — default `snippet`; truncation is display-only. Prefer `--format json --detail raw` when exact whitespace must match storage.

For full flag semantics, use `--help` on each subcommand. Agent-facing operational detail stays in the `sr-*` skill files — this page does not fork those tables.

## Warehouse location

Default home is `$XDG_DATA_HOME/stockroom` or `~/.local/share/stockroom`, overridable with `STOCKROOM_HOME`. The DuckDB warehouse file lives under that home.

Optional overrides for ingest roots and enrichment: `STOCKROOM_CURSOR_ROOT`, `STOCKROOM_CLAUDE_ROOT`, `STOCKROOM_AI_TRACKING_DB`.

## Raw DuckDB

When you want ad-hoc SQL outside the `stockroom query` presentation layer, open the warehouse with the [DuckDB CLI](https://duckdb.org/docs/stable/clients/cli/overview) in **read-only** mode so you cannot accidentally write. Prefer `stockroom query` for routine work — it already opens read-only and applies the project’s detail/format conventions.

Exact filename under stockroom home can move with migrations; if unsure, ask the agent or inspect `$STOCKROOM_HOME` after a successful initialize.
