# Warehouse

The DuckDB warehouse as rebuildable ETL output, and the doctrines that shape what it stores and how processes open it.

## What the warehouse is

Rebuildable projection of harness history — not the system of record — how rows get in, and read surfaces that cannot write by construction.

### Rebuildable ETL

The warehouse is a single-file DuckDB database under stockroom home (`$XDG_DATA_HOME/stockroom` or `~/.local/share/stockroom`, overridable via `STOCKROOM_HOME`). It is rebuildable ETL from the harnesses’ own session records — never the system of record. Ingestion re-derives rows from those sources; the warehouse is the queryable projection.

### Ingest pipeline

Per-harness parsers emit shared dataclasses; the writer is the only SQL touchpoint. Default ingest is incremental (per-harness watermarks in `_sync_state`). The warehouse is allowed to **outlive its sources**: rows whose transcripts later vanish are never pruned. Observation-time fields (for example `messages.first_seen_at`) are not rebuildable from sources alone — that is why “delete and re-ingest” is not a free reset of every column.

### Read-only by construction

The read surfaces (`query`, `semantic`) open the warehouse read-only at the connection level — DuckDB itself rejects writes through them. “You cannot corrupt anything by querying” is a property of the connection mode, not of good manners.

## What we store

Fidelity doctrines: which fields are kept, whole text at rest, uniform identity, honest workspace paths, and UTC timestamps.

### Kept fields

Shared tables are `sessions`, `messages`, `tool_calls`, `embeddings`, and `_sync_state`. Prompts and responses are stored whole; tool *inputs* are kept; tool *result* payloads are dropped. Thinking/reasoning blocks the harness keeps separate are not stored. There is no raw mirror layer beside the typed model.

### No truncation at rest

Kept fields are stored whole. Truncation is a **read-time** display bound so one fat column does not flood a context window. Elision markers report how much was withheld; the full content remains in the warehouse for a targeted re-fetch. Both read surfaces print through one render chokepoint (`--detail` / `--format`); see [Embeddings](embeddings.md#read-time-rendering) for the search-side note and [Advanced → CLI](../advanced/cli.md) for flags.

### Harness-labeled identity

Every row carries a `harness` column. Columns mean one thing independent of harness — extraction may differ; meaning must not. Identity is uniform: `(harness, session_id)` for sessions, `message_id = '{session_id}#{ordinal}'` for messages. Native harness identifiers are demoted to `source_*` provenance — kept for traceability, never used as join keys, because they exist at different grains and formats per harness. A value that only exists for one harness is `NULL` for the other, never fabricated.

### Workspace identity

`sessions.project_id` is the harness slug verbatim; `sessions.cwd` is best-effort real path, `NULL` when unknown. Path candidates are accepted only when encoding them for that harness reproduces the slug — verify, don’t invert. Guessing a workspace from a slug without that check invents false identity.

### UTC timestamps

DuckDB `TIMESTAMP` is timezone-naive; Stockroom’s contract is that every persisted value is **UTC wall clock**. Clients that display times own timezone rendering.

## How we open and evolve it

Connection chokepoints, concurrency, and forward-only schema migrations.

### Concurrency and open paths

Every consumer reaches DuckDB through a warehouse chokepoint:

- **`open()`** — path resolution, lazy migration, VSS load. Writers take an exclusive coordination flock for the connection’s lifetime; readers open read-only and back off to a typed busy error when the file stays locked.
- **`open_current()`** — the dashboard exception: read-only, **no migrate**, typed stale/busy errors. A UI process must not become the migrator mid-browse.

Coordination uses `fcntl.flock` on a sidecar lock file; data integrity uses DuckDB’s own file lock. Those are two layers with different jobs — do not collapse them into “just open the file.”

### Migrations

Migrations are numbered forward-only SQL under the engine’s `migrations/` tree; `schema_version` is runner-owned. Schema changes go through the `open()` chokepoint — Architecture does not list DDL here.

## Related procedures

- Operating ingest/embed/schedule: [User Guide → Load the Warehouse](../user-guide/ingest.md)
- Escape-hatch SQL: [Advanced → CLI](../advanced/cli.md)
- Contributor engine/schema work: [Contributing → Iteration](../contributing/iteration.md)
