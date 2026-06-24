# Project Brief — Phase 1: Schema, Database, Ingest, and Migrations

## User Story

Phase 0 (Foundations) is complete and verified green. Begin **Phase 1** of `planning/roadmap.md`: build the faithful data backbone — the reason stockroom is worth using at all. By the end of Phase 1 a real ingest of the operator's own Cursor and Claude Code history lands faithfully in a queryable DuckDB warehouse, with a safe, forward-only migration system underneath it and `sr-query` as the first user-facing surface.

## Scope

Phase 1 is a multi-milestone phase, to be executed as a Level 4 project — one milestone at a time, each as its own L1–L3 sub-run, in dependency order:

1. **Schema field enumeration + locked DDL** — point an agent at real Cursor and Claude Code transcripts side by side, enumerate every exposed field, and lock one shared, harness-labeled set of tables (sessions, messages, tool calls inputs-only, plan documents, embeddings, sync-state watermark). Each row carries a `harness` column — never separate per-harness tables. Includes the stable message-identity contract and conversation-reconstruction keys (conversation id, parent/child, ordering, subagent↔parent, model-per-chain). Test-first against real and pathological fixtures. `cursor-warehouse`'s schema may be reused; `claude-warehouse`'s may not (clean-room).
2. **Migration framework** — numbered one-per-file SQL migrations inside the skill, a `schema_version` record, the lazy gate (each consumer checks version before touching the DB), forward-only application under an exclusive lock, concurrency-safe reader degradation. The locked schema ships as the first migration. Lock primitive and reader wait/backoff semantics chosen here.
3. **Trace ingest (ETL)** — incremental, per-source watermarked (`last_mtime` / `last_path`) with a `--full` reset; both Cursor and Claude Code (Claude Code parsed clean-room from its native on-disk format); subagents included and linked to parents; kept content stored untruncated; tool inputs only, no outputs, no raw layer; WSL/Windows-mount-aware path resolution; optional model/labeling enrichment from Cursor's `ai-code-tracking.db` limited to model/labeling fields.
4. **`sr-query`** — raw SQL against the warehouse: the first user-facing surface, proving the database is real and queryable end to end.

## Done When

A real ingest of the operator's own Cursor and Claude Code history lands faithfully — kept fields stored whole and verified against the source, subagents linked to parents — `sr-query` returns correct results over it, and the migration suite proves a schema-changing upgrade is safe and data-preserving under concurrent reader/writer load.

## Constraints

- Test-first (TDD), per the workspace rule.
- Both harnesses from day one; Claude Code parsed clean-room from its own on-disk format.
- Builds on the Phase 0 substrate: locked uv project in `skills/sr-search/`, torch held out of the lock, `make` as the dev entrypoint.
- Authoritative source artifacts (`pyproject.toml`, `uv.lock`, migration SQL) take precedence over roadmap prose once they exist.
