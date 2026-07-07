# Active Context

## Current Task: `sr-search` skill (p2-embeddings-search m6)
**Phase:** BUILD - COMPLETE

## What Was Done
- Full rewrite of `skills/sr-search/SKILL.md` (36 lines, skeleton → judgement skill): front-matter flipped to `enable-model-invocation: true` with the routing-bearing description; routing table shipping the four desk-check cases as the skill's own examples (preflight amendment); synthesis rules as six actionable lines (narrated default, list-on-request, id dedup with found-both-ways signal, no cross-surface score math, truncation-by-delegation, relaying posture); one-line engine-home breadcrumb.
- Delegation per the creative: sibling skills named, one relative-path fallback (`../sr-query/SKILL.md`, `../sr-semantic/SKILL.md`), **no invocation section** — grep-verified zero forbidden tokens (`APP_DIR`, `PYTHONPATH`, `uv run`, `--no-sync`, `--no-config`, `python -m`).
- Live end-to-end passes against the real warehouse: exact ask (sessions per harness → 731 cursor / 39 claude via `sr-query`), meaning ask (warehouse-locking debug via `sr-semantic`, relevant ranked hits), both-surfaces ask (REUSE licensing: `ILIKE` scan + semantic `--format json`, ids in hand for dedup).
- Gates: `make localdev` (3 skills symlinked), `make ci` fully green (266 passed, 2 skipped; ruff, lock-check, REUSE all pass; `test_skeleton_skill_front_matter` green through the flip), torch restored after CI sync stripped it (`make torch`, smoke-checked), sibling cross-references verified — no edits needed.

## Key Build Decisions
- One addition beyond the plan's letter: a fallback line ("if the routed surface comes back empty or thin, try the other surface") — actionable guardrail consistent with `sr-semantic`'s switch-strategy advice.
- No deviations otherwise: no sibling, manifest, or `REUSE.toml` edits (as planned).

## Next Step
- QA phase (runs automatically per L3 workflow).
