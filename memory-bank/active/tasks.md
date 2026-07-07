# Task: `sr-search` skill (p2-embeddings-search m6)

* Task ID: p2-embeddings-search-m6
* Complexity: Level 3
* Type: feature (prose skill authoring)

Rewrite `skills/sr-search/SKILL.md` from its Phase-0 skeleton into the real judgement skill: the friendly default search entrypoint that (1) judges whether a question is an exact/structured lookup, a meaning-based recall, or both; (2) delegates to the `sr-query` / `sr-semantic` sibling skills accordingly; (3) merges/ranks and presents a context-truncated answer. No Python fusion module (settled: `creative/creative-search-surface-architecture.md`, Option 3). Front-matter flips to `enable-model-invocation: true` with a routing-bearing description.

**Operator constraint (binding this sub-run):** author lean per `planning/brainstorm/skill-litter-audit.md` — the skill carries *task knowledge only* (routing cues, delegation instructions, synthesis/presentation rules, guardrails-as-actions). No Category A rationale, no Category B doubled content (especially: do not restate the siblings' operational advice or the engine incantation), no Category C narration. The audit's "m6 inherits the invocation litter temporarily" concession applies only *if* the skill needs an invocation section at all — the delegation design may eliminate it entirely.

## Component Analysis

### Affected Components

- `skills/sr-search/SKILL.md`: currently the honest skeleton (engine-home description, entrypoint inventory, sibling invocation contract; `enable-model-invocation: false`) → full rewrite into the judgement skill. The engine itself (everything else under `skills/sr-search/`) is untouched.
- `skills/sr-query/SKILL.md` / `skills/sr-semantic/SKILL.md`: already route ambiguity to `sr-search` ("when you are not sure which is right, that judgement belongs to the **`sr-search`** skill") → expected **no edits**; verify the references still read correctly once `sr-search` is real.
- `.cursor-plugin/plugin.json` / `.claude-plugin/plugin.json`: skill auto-discovery → no edits (m4/m5 precedent).
- `REUSE.toml`: `skills/**` PPL-S glob covers the rewritten file → no edits.
- `.cursor/skills/stockroom-local/` localdev mirror: refresh via `make localdev` after the rewrite.
- `memory-bank/systemPatterns.md` (skeleton-skill convention cites `sr-search` as the living example) and `memory-bank/techContext.md`: reconciliation is REFLECT work (m4/m5 precedent), not build tasks.

### Cross-Module Dependencies

- `sr-search` → `sr-query` skill and `sr-search` → `sr-semantic` skill: prose delegation (the deciding axis of the architecture creative). The siblings are the single home for per-surface operational advice; `sr-search` must lean on them, never restate them.
- `sr-search` directory → shared engine: co-location only. The rewrite must preserve (somewhere minimal) the fact that this directory hosts the engine, without re-becoming the engine's documentation surface (the README + `systemPatterns.md` already own that for developers).

### Boundary Changes

- Front-matter: `enable-model-invocation: false → true`; description changes from placeholder to the routing contract ("the friendly default; use when unsure between exact and meaning-based search"). This is the skill's public interface to both harnesses' model-invocation routing.
- No engine, schema, or manifest changes.

### Invariants & Constraints

- No duplication of per-surface operational knowledge (architecture creative, quality attribute #2) — reinforced by the operator's litter constraint.
- Prompt-skill behavior verified artisanally; TDD binds Python only (none planned).
- Authored against the *current* invocation contract (on-path CLI is Phase 4); but prefer designs where `sr-search` carries no incantation at all.
- Read-only posture throughout; truncation guidance references the siblings' existing `--detail` discipline rather than restating it.

## Open Questions

- [x] **Delegation mode** → Resolved: delegate by sibling skill *name* with a single relative-path fallback note (`../sr-query/SKILL.md`, `../sr-semantic/SKILL.md`); no invocation section in `sr-search` at all (see `memory-bank/active/creative/creative-sr-search-delegation-mode.md`).
- [x] **Synthesis grain** → Resolved: narrated answer citing evidence by default; one merged judgement-ordered list when the ask is list-shaped; dedup by `message_id`/`session_id` (found-both-ways = strong relevance); never blend scores across surfaces (see `memory-bank/active/creative/creative-sr-search-synthesis-grain.md`).

## Test Plan (TDD)

To be completed after the open questions resolve (artisanal verification plan — no Python planned).

## Implementation Plan

To be completed after the open questions resolve.

## Status

- [x] Component analysis complete
- [ ] Open questions resolved
- [ ] Test planning complete
- [ ] Implementation plan complete
- [ ] Technology validation complete
- [ ] Preflight
- [ ] Build
- [ ] QA
