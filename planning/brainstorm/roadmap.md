# Brainstorm — Roadmap

Rough phasing to seed the **Roadmap** document. This is a sketch, not the final plan — the real roadmap is authored after the Tech Brief is solid (and after the torch spike, O9, lands). Phases are roughly ordered by dependency, not committed to a schedule.

> **Superseded (2026-07-08):** the authoritative `planning/roadmap.md` since **swapped Onboarding ahead of the Dashboard** (Phase 3 = Onboarding, CLI, and Scheduling; Phase 4 = Dashboard) so onboarding establishes the on-path `stockroom` invocation contract before the dashboard is built on it. The Phase 3/4 labels below reflect the *original* sketch order; defer to the authoritative roadmap and `memory-bank/active/creative/creative-roadmap-resequencing.md`.

## Guiding Shape

The intended end-to-end user experience defines the spine: **install the plugin → run `sr-initialize` → it sets up overnight re-ingest/re-embed and performs a first ingest + embed → open the dashboard to see what you've been up to → thereafter use `search` / `semantic` / `query` to inspect history.** The phases below build toward that, bottom-up.

## Phase 0 — Foundations

- Repo scaffolding under the dual-manifest plugin template (`.cursor-plugin`, `.claude-plugin`, `skills/`), AGPLv3 in place, release-please wired.
- The uv project skeleton (`pyproject.toml` + `uv.lock`) inside the app-bearing skill directory.
- **Resolve the torch spike (O9)**: prove out "lock everything except torch" before building on it.
- **Study the Cursor and Claude Code transcript formats side by side** — enumerate the fields each exposes — and design the faithful, harness-general conversation schema (no truncation at rest; ETL into our shape, no raw layer; core fields + subagent↔parent linkage + plan-doc artifacts + reconstruction keys, D21/D22) before committing to tables.

## Phase 1 — Ingest, Database, Migrations

- DuckDB schema (sessions / messages / tool calls (inputs) / plan documents / embeddings; harness-labeled; subagent↔parent + conversation-reconstruction linkage; content stored untruncated, no raw layer).
- The migration framework: numbered SQL files, `schema_version`, exclusive-lock application, lazy gate, concurrency safety. This is foundational productization and comes early on purpose.
- Trace ingest (incremental, watermarked, subagents included; WSL/mount-aware path resolution) — **ETL into our schema, content untruncated; no tool outputs, no raw copy**; **both Cursor and Claude Code in v1** (O12 resolved), Claude Code parsed clean-room from its native format.
- `sr-query` (raw SQL) — the first usable surface, validating the DB end to end.

## Phase 2 — Embeddings and Search

- The embedding pipeline (`sentence-transformers`, chunk + mean-pool, HNSW), built on the Phase 0 torch outcome.
- `sr-semantic` (pure vector search).
- `sr-search` (blended keyword + semantic entrypoint).

## Phase 3 — Dashboard

- Metrics computation + local web server + front-end (vendored assets).
- `sr-dashboard` (on-demand launch + URL) and the idempotent, fire-and-forget session-start hook.

## Phase 4 — Onboarding and Scheduling

- `sr-initialize`: prerequisite checks, torch verification, nightly cron/launchd install with correct absolute-path resolution, and the first full ingest + embed.

## Phase 5 — Distribution and Release

- Marketplace entry in `txrk9-agent-plugins`, install docs, release-please release flow, end-to-end install test.

## Future (Post-v1)

- **Recap** as a time-series over dashboard metrics.
- **Additional harnesses beyond Cursor + Claude Code** (Codex, Windsurf, …), leveraging the harness-labeled schema.
- AI-code attribution, token/cost estimation, source-file purge — only if/when warranted.

## Sequencing Notes

- Migrations land in Phase 1, not bolted on later, because "never break the user's DB" is a core promise and retrofitting migrations is painful.
- The torch spike gates Phase 2; do it in Phase 0 so it can't ambush the embedding work.
- `sr-query` before the search skills gives a working, inspectable DB as early as possible.
