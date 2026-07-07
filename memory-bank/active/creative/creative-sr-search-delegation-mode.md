# Architecture Decision: `sr-search` Delegation Mode

> m6 sub-run creative. The search-surface architecture creative (Option 3) decided `sr-search` delegates to the sibling *skills*, not the engine modules — but left the mechanics open: how does prose in one skill "delegate" to another skill?

## Requirements & Constraints

Quality attributes, ranked:

1. **No duplication of operational knowledge** — the binding constraint from the architecture creative, reinforced by the operator's litter directive for this sub-run. Whatever the mechanism, `sr-query`/`sr-semantic` content must not be restated in `sr-search`.
2. **Works in both harnesses** — Cursor and Claude Code both ship this plugin; the delegation must not depend on a mechanism only one harness has.
3. **Reliable at execution time** — when `sr-search` is invoked, the agent must actually end up operating with the sibling's guidance in hand, not improvising a call from memory.
4. **No new litter** — no path-resolution plumbing, no incantations, no rationale.

Context: all three skills live side-by-side in the same plugin (`skills/sr-query/`, `skills/sr-semantic/`, `skills/sr-search/`). The siblings are model-invocable with routing-bearing descriptions, and each carries the full operational contract for its surface (invocation, flags, guardrails, error tables, worked examples). Skills are plain files on disk in every install; an agent that knows one skill's location can reach a sibling with a relative path.

## Components

`sr-search` (judgement) → routes to → `sr-query` skill and/or `sr-semantic` skill (operational contracts) → engine CLIs → warehouse. The question is only the arrow between the skills.

## Options Evaluated

- **Option A — Delegate by skill name, relative-path fallback**: `sr-search` names the sibling skill ("consult and follow the `sr-query` skill") and notes, once, that the sibling files sit beside this one (`../sr-query/SKILL.md`, `../sr-semantic/SKILL.md`) for direct reading when the harness doesn't surface skills by name.
- **Option B — Delegate by explicit file read with resolved paths**: `sr-search` instructs a `$PLUGIN_ROOT`-based resolution of the sibling SKILL.md paths and a mandatory read before acting.
- **Option C — Inline the sibling commands**: `sr-search` carries its own runnable `stockroom.query`/`stockroom.semantic` command forms so the agent never has to leave the file.

## Analysis

| Criterion | A — name + relative fallback | B — resolved file read | C — inline commands |
|-----------|------------------------------|------------------------|---------------------|
| No duplication (#1) | ✓ nothing restated | ✓ nothing restated | ✗ re-encodes invocation + flags — the exact drift setup the m4 fix repaired |
| Both harnesses (#2) | ✓ names work everywhere skills do; relative path is harness-neutral | ~ `CURSOR_PLUGIN_ROOT` vs. Claude equivalent — per-harness plumbing | ✓ |
| Reliable in hand (#3) | ✓ named skill or one-line relative read | ✓ | ✗ commands without the guardrails around them |
| No new litter (#4) | ✓ one sentence | ✗ reintroduces the resolution block the litter audit flags as the largest cluster | ✗ largest possible duplication |

Key insights:

- Option C is already rejected by the search-surface architecture creative (it *is* Option 2 of that analysis wearing prose clothes) — it re-encodes every safeguard the wrappers exist to hold.
- Option B duplicates the `$APP_DIR` resolution *pattern* purely to find a text file that is guaranteed to sit at a fixed relative location. Skills-relative addressing needs no environment variable: the three skills ship as siblings in every install layout (committed layout = install layout, no build step).
- Option A's two halves cover both harness postures: where the harness surfaces skills by name (both do, via model-invocation descriptions), the name suffices; where an agent only has the `sr-search` file in hand, `../sr-query/SKILL.md` is a one-hop read with zero plumbing.

## Decision

**Selected**: **Option A** — delegate by sibling skill *name*, with a single parenthetical noting the siblings live beside this skill (`../sr-query/SKILL.md`, `../sr-semantic/SKILL.md`) for direct reading.

**Rationale**: The only option that satisfies the no-duplication constraint (#1) *and* adds no plumbing (#4). It composes with how both harnesses already surface the siblings (routing-bearing descriptions, `enable-model-invocation: true`), and the relative-path fallback makes delegation deterministic even for an agent holding only this file.

**Tradeoff**: `sr-search` cannot be executed "self-contained" — an agent must load a sibling before running anything. Accepted: that is the *point* of the architecture (judgement here, operations there), and a self-contained `sr-search` is definitionally the duplication we rejected.

## Implementation Notes

- Delegation language is imperative and action-shaped: "route the question, then **follow the chosen sibling skill** for how to run the search" — not a description of the architecture.
- One relative-path note, stated once where delegation is introduced; never repeated per-branch.
- Consequence for the litter constraint: `sr-search` needs **no invocation section at all** — no `$APP_DIR`, no `PYTHONPATH`, no uv flags. The audit's "m6 temporarily inherits the invocation litter" concession is mooted by this design.
