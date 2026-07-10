# Product Context

Stockroom turns agentic-coding history (Cursor and Claude Code) into a local, private, searchable single-file DuckDB warehouse. Kept content is stored whole — truncation is a read-time convenience, never a storage-time loss. It ships as a dual-manifest plugin (shared `skills/` tree for Cursor and Claude Code) with no build step: the committed layout is the install layout. Surfaces are a small set of skills — blended search, semantic search, raw SQL, and an at-a-glance dashboard — plus one-command machine setup via `sr-initialize`.

## Target Audience

Privacy- and supply-chain-conscious power users of agentic coding harnesses. They install a Cursor or Claude Code plugin, run an initialization skill, and expect the tool to stay local, pinned, and auditable. Machines are heterogeneous, including a real WSL/Windows-mount contingent.

## Use Cases

- Find a past conversation by keyword, meaning, or both (`sr-search`).
- Recall by meaning when exact words won't match (`sr-semantic`).
- Ask arbitrary questions with read-only SQL (`sr-query`).
- See recent activity at a glance (`sr-dashboard`).
- Stay current automatically via nightly ingest + embed after `sr-initialize`.
- Survive schema upgrades through forward-only migrations without stranding the warehouse.

## Key Benefits

- Faithful recall: prompts, responses, and tool inputs are stored in full; reads apply deliberate, context-aware truncation.
- Local and private: data and embedding computation stay on the machine; no telemetry; no cloud APIs for core function.
- Supply-chain safe: locked, hash-verified `uv` project (torch held out of the lock and provisioned per-machine).
- Doesn't break your data: migrations with concurrency-safe locking; readers degrade cleanly under writers.
- Harness-labeled schema ready for additional harnesses later.

## Success Criteria

A user can install from the marketplace, run `sr-initialize`, and use `sr-search`, `sr-semantic`, `sr-query`, and `sr-dashboard` against real Cursor and Claude Code history. Kept content is complete at rest. Schema-changing upgrades preserve data under concurrent load. The tool is good enough for daily personal use and clean enough to ship.

## Key Constraints

- No truncation at rest; truncation only at read time.
- Local-only: no telemetry, no cloud; network use is package fetch and the local dashboard.
- AGPLv3 (including the network-served dashboard).
- uv-locked except torch (per-machine wheel).
- Both Cursor and Claude Code ingested; both plugin manifests ship.
- Session-start hook: idempotent, fire-and-forget, never errors; launches dashboard (and rectifies the on-path shim) — never ingests or migrates.
