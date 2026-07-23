# DuckDB

Open the warehouse with the [DuckDB CLI](https://duckdb.org/docs/stable/clients/cli/overview) when you need ad-hoc SQL outside the `stockroom query` presentation layer.

## Warehouse path

The warehouse file is `$STOCKROOM_HOME/warehouse.duckdb`. Default home is `$XDG_DATA_HOME/stockroom` or `~/.local/share/stockroom`. Full path topology: [Installed layout](../user-guide/installed-layout.md).

```bash
echo "${STOCKROOM_HOME:-${XDG_DATA_HOME:-$HOME/.local/share}/stockroom}/warehouse.duckdb"
```

## Open read-only

Always open read-only so you cannot accidentally write:

```bash
duckdb -readonly "${STOCKROOM_HOME:-${XDG_DATA_HOME:-$HOME/.local/share}/stockroom}/warehouse.duckdb"
```

Then run SQL interactively, or pass a one-shot statement:

```bash
duckdb -readonly "${STOCKROOM_HOME:-${XDG_DATA_HOME:-$HOME/.local/share}/stockroom}/warehouse.duckdb" -c "SELECT COUNT(*) FROM sessions"
```

(`-readonly` is a DuckDB CLI flag — see `duckdb --help`.)

## Prefer stockroom query

For routine lookups, prefer `stockroom query`. It already opens the warehouse read-only and applies the project's `--format` / `--detail` conventions. Reach for raw DuckDB when those conventions get in the way (exploratory joins, DuckDB-native tooling, or SQL you do not want wrapped by the presentation layer).

See [CLI](cli.md) for out-of-band `stockroom` invocation.

## Caveats

- **Do not write** through the DuckDB CLI. Schema and ETL go through the engine (`ingest` / `embed` / migrations). Opening without `-readonly` risks corrupting a live warehouse.
- **Locks**: ingest, embed, and other writers may hold locks. If open fails or hangs, stop writers or wait — see [Architecture → Warehouse](../architecture/warehouse.md) for the lock model.
- **No presentation layer**: raw DuckDB will not apply Stockroom's detail/format truncation. Large text columns can flood your terminal.
- **Migrations**: the on-disk schema is versioned by the engine. Do not hand-edit schema in the DuckDB CLI; contributor schema work belongs in [Contributing → Iteration](../contributing/iteration.md).

## See also

- [CLI](cli.md) — `stockroom query` / `semantic` with format and detail
- [Architecture → Warehouse](../architecture/warehouse.md) — what is stored and how locks/migrations work
- [Search](../user-guide/search.md) — product how-to for asking questions
