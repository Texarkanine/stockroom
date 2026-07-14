# stockroom

**A local, faithful, searchable warehouse of your agentic-coding history.**

Stockroom captures prompts, responses, and tool inputs from [Cursor](https://cursor.com/) and [Claude Code](https://code.claude.com/) into a single-file [DuckDB](https://duckdb.org/) warehouse with local [`sentence-transformers`](https://www.sbert.net/) embeddings. Kept content is stored **whole** — truncation is a read-time convenience, never a storage-time loss.

Day-to-day use is agent-native: ask about past work, or slash-invoke `/sr-search` and companions so the harness can assemble the right lookup for you. Heck, your agents might even reach for it themselves when they need to know about past work!

You're not locked in to inference, though: after setup it can run **fully offline** — query the warehouse with the local `stockroom` or `duckdb` CLIs, no agent required!

## Why stockroom?

- **Faithful history** — full prompts, responses, and tool inputs in one local warehouse, not a truncated scrapbook.
- **Skill-first** — day-to-day use is ask-the-agent or slash-invoke `sr-*`; the CLI is an escape hatch after setup.
- **Local by design** — DuckDB + on-machine embeddings; no cloud index of your coding sessions.
- **Two harnesses, one tree** — Cursor and Claude Code share the same skills and engine.

## Quickstart

1. Add the [`txrk9-agent-plugins`](https://github.com/Texarkanine/txrk9-agent-plugins) marketplace and install `stockroom`.
2. **Cursor only:** enable **Include third-party Plugins, Skills, and other configs** (Settings → Rules, Skills, Subagents) so plugin hooks register.
3. Run first-time setup:
   - **Cursor:** `/sr-initialize`
   - **Claude Code:** `/stockroom:sr-initialize`
4. Ask the agent about past work, or slash-invoke `/sr-search` (Claude: `/stockroom:sr-search`).

Full walkthrough (prerequisites, what landed on disk, what to try next): [Quickstart](https://texarkanine.github.io/stockroom/user-guide/quickstart/).

## Documentation

- [Quickstart](https://texarkanine.github.io/stockroom/user-guide/quickstart/) — step-by-step guide to setup and use
- [User guide](https://texarkanine.github.io/stockroom/user-guide/) — How each of the various pieces work
- [Architecture](https://texarkanine.github.io/stockroom/architecture/) — high-level tour of the system
