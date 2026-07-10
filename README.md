# stockroom

A local, faithful, searchable warehouse of your agentic-coding history.

Stockroom captures prompts, responses, and tool inputs from Cursor and Claude Code into a single-file [DuckDB](https://duckdb.org/) warehouse with local [`sentence-transformers`](https://www.sbert.net/) embeddings. Kept content is stored **whole** — truncation is a read-time convenience, never a storage-time loss.

It ships as a **dual-manifest plugin** (one shared `skills/` tree for Cursor and Claude Code) with **no build step**: the committed layout is the install layout.

## Install

Add the [`txrk9-agent-plugins`](https://github.com/Texarkanine/txrk9-agent-plugins) marketplace, install `stockroom`, then run first-time setup:

- **Cursor:** `/sr-initialize`
- **Claude Code:** `/stockroom:sr-initialize`

Full install paths (marketplace and local/dev load): [docs/using.md](docs/using.md).

## Skills

| Skill | Role |
| --- | --- |
| `sr-initialize` | Machine setup (torch, on-path CLI, schedule, first ingest) |
| `sr-search` | Friendly default search (routes to query / semantic) |
| `sr-query` | Read-only SQL against the warehouse |
| `sr-semantic` | Meaning-based (vector) search |
| `sr-dashboard` | Local metrics dashboard |

Harness-specific slash forms and post-setup usage: [docs/using.md](docs/using.md).

## Development

Contributor workflow (Makefile, torch-safe run contract, on-path `stockroom` shim): [docs/development.md](docs/development.md).

## License

Layered, and enforced by `reuse lint` (see [`REUSE.toml`](REUSE.toml)): code is [AGPL-3.0-or-later](LICENSES/AGPL-3.0-or-later.txt); prompt-shaped skill content is layered under the Public Prompt License (PPL-S).
