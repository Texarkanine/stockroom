# stockroom

A local, faithful, searchable warehouse of your agentic-coding history.

Stockroom captures prompts, responses, and tool inputs from Cursor and Claude Code into a single-file [DuckDB](https://duckdb.org/) warehouse with local [`sentence-transformers`](https://www.sbert.net/) embeddings. Kept content is stored **whole** — truncation is a read-time convenience, never a storage-time loss.

It ships as a **dual-manifest plugin** (one shared `skills/` tree for Cursor and Claude Code) with **no build step**: the committed layout is the install layout.

> **Docs:** [texarkanine.github.io/stockroom](https://texarkanine.github.io/stockroom/) · source under [`docs/`](docs/)

## Why stockroom?

- **Faithful history** — full prompts, responses, and tool inputs in one local warehouse, not a truncated scrapbook.
- **Skill-first** — day-to-day use is ask-the-agent or slash-invoke `sr-*`; the CLI is an escape hatch after setup.
- **Local by design** — DuckDB + on-machine embeddings; no cloud index of your coding sessions.
- **Two harnesses, one tree** — Cursor and Claude Code share the same skills and engine.

## Quickstart

1. Add the [`txrk9-agent-plugins`](https://github.com/Texarkanine/txrk9-agent-plugins) marketplace and install `stockroom`.
2. Run first-time setup:
    - **Cursor:** `/sr-initialize`
    - **Claude Code:** `/stockroom:sr-initialize`
3. Ask the agent about past work, or slash-invoke `/sr-search` (Claude: `/stockroom:sr-search`).

What landed on disk: [Installed layout](docs/user-guide/installed-layout.md).

## Skills

| Skill | Role |
| --- | --- |
| `sr-initialize` | Machine setup (torch, on-path CLI, schedule, first ingest) |
| `sr-search` | Friendly default search (routes to query / semantic) |
| `sr-query` | Read-only SQL against the warehouse |
| `sr-semantic` | Meaning-based (vector) search |
| `sr-dashboard` | Local metrics dashboard |

Harness-specific slash forms: [Skill index](docs/user-guide/skills.md).

## Documentation

- [User guide](docs/user-guide/quickstart.md) — quickstart, installed layout, troubleshooting, advanced CLI
- [Architecture](docs/architecture/index.md) — human tour; agent doctrines stay in `system-model.md`
- [Contributing](CONTRIBUTING.md) — how to land a change

## License

Layered, and enforced by `reuse lint` (see [`REUSE.toml`](REUSE.toml)): code is [AGPL-3.0-or-later](LICENSES/AGPL-3.0-or-later.txt); prompt-shaped skill content is layered under the Public Prompt License (PPL-S). Details: [Licensing](docs/contributing/licensing.md).
