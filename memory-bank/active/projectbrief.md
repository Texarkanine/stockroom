# Project Brief

## User Story

As an operator (or agent using `sr-query`), I want a discoverable query cookbook for token VIEW rollups, per-harness skill-use SQL, and tool-use SQL so that I can get the full tables without reverse-engineering the dashboard API or re-deriving gnarly harness-specific queries.

## Use-Case(s)

### Use-Case 1

An agent needs the full skill-use or tool-use table (beyond dashboard top-10). It opens `sr-query`, finds the cookbook, and runs the documented pure SQL for the relevant harness.

### Use-Case 2

A human reads the docs site Advanced cookbook pages, copies a starter query from an inlined recipe (snippet-included from the skill SSOT), and runs it via `stockroom query` or DuckDB.

### Use-Case 3

An agent hits a gnarly token-rollup or skill/tool question already covered by an inline example in `SKILL.md`; the useful short example remains, with a thoughtful pointer to the cookbook when more variants exist — not a blanket “go load the cookbook.”

## Requirements

1. Implement the query cookbook architecture from `memory-bank/active/creative/creative-query-cookbook.md` (Option B): SSOT under `skills/sr-query/references/cookbook/`, docs advanced pages that `pymdownx.snippets`-include recipe bodies, discoverable from `sr-query` (and related skills where appropriate).
2. Populate recipes for: VIEW/`session_token_usage` starters; pure SQL skill-use per harness (Claude + Cursor); pure SQL tool-use (cross-harness / per harness as needed) — as described in [#69](https://github.com/Texarkanine/stockroom/issues/69).
3. Thoughtfully cross-link from existing in-skill agent docs: reference the cookbook where explicitly appropriate instead of repeatedly inlining the same gnarly queries; keep useful inline examples; do not replace a tight single-example page with a vague “load the cookbook” that buries the relevant recipe.
4. Cookbook must be discoverable (index from `SKILL.md`, human TOC under `docs/advanced/`).
5. Update `properdocs.yaml` comment to reflect intentional dual-audience cookbook includes.

## Constraints

1. One SSOT for recipe bodies (skill cookbook); docs wrappers own human when/why prose.
2. Do not park a user-guide corpus under `skills/**/references/` — recipes stay short (when + SQL + caveats).
3. User-guide pages stay pointer-only into the advanced cookbook (no cloned SQL).
4. Pure SQL for skills/tools as requested for #69 (operator-approved); harness drift risk acknowledged — document drift triggers on recipes.
5. Dual-manifest plugin: cookbook lives under shared `skills/` tree (mirrored into `.cursor/skills/stockroom-local/` if that is the project’s install sync pattern — follow existing conventions).

## Acceptance Criteria

1. `skills/sr-query/references/cookbook/` exists with an index and recipes covering token VIEW, skill-use (both harnesses), and tool-use.
2. `docs/advanced/` cookbook page(s) render those recipe bodies via snippets; site builds cleanly.
3. `sr-query/SKILL.md` (and any other in-skill docs that warrant it) discoverably points at the cookbook without stripping useful inline examples.
4. An operator can answer “full skills/tools table” and “token rollup starters” from the cookbook without reverse-engineering dashboard endpoints.
5. Issue #69 intent is satisfied for the scoped recipe set.
