# Active Context

## Current Task: `sr-semantic` skill (p2-embeddings-search m5)
**Phase:** PLAN - COMPLETE

## What Was Done
- L4 re-entry (Step 2a): m4 checked off; ephemerals cleared; classified m5 (`sr-semantic` skill) as **Level 2** (self-contained prose-skill authoring, design settled by the search-surface architecture creative + `print-for-who.md`; m4 precedent).
- Surveyed the wrapped surface (`stockroom.semantic` CLI: `-k/--limit`, `--format`, `--detail`, exit codes 0/1/2 and stderr forms; `render.format_semantic` columns `rank score harness role preview`, json adds ids + numeric score) and the m4 `sr-query` SKILL.md as the structural template.
- Wrote the full Level 2 plan to `tasks.md`: 7 ordered steps (front-matter → routing/query-phrasing → invocation contract with the torch-at-query-time caveat → output discipline → guardrails incl. the `sr-query` full-text handoff → verified worked examples → integration checks + `make ci`/`make torch` gate).

## Key Plan Decisions
- Prose-only, no helper `scripts/`, no Python — TDD passes by project-invariant exemption; verification is artisanal (every shipped example executed live before being written in) + `make ci` green.
- The canonical full-text fetch for a semantic hit is a **handoff to `sr-query` by `message_id`** (json format carries the ids) — skill composability over re-implementing a fetch.
- Surface-specific torch guardrail: this CLI needs torch at query time (query embedding); torch-missing is an environment problem (`make torch`), never a retry loop.
- No `sr-search/SKILL.md`, `plugin.json`, or `REUSE.toml` edits expected (m4-corrected invocation block already in place; auto-discovery; glob-covered).

## Next Step
- Preflight validation (autonomous).
