# Decision: `sr-search` Synthesis Grain

> m6 sub-run creative. `milestones.md` defers to this sub-run: what does `sr-search` produce — a fused ranked list, a narrated answer, or both?

## Context

`sr-search` routes a question to `sr-query`, `sr-semantic`, or both, then "merges/ranks and presents a context-truncated answer." The grain of that presentation must be decided before the skill's synthesis section can be written. It matters because the both-surfaces case hands the agent two result sets with **incomparable orderings** — SQL rows (no score, ordered by whatever the query said) and semantic hits (relative cosine similarity, explicitly not thresholdable per the `sr-semantic` skill) — and a wrong rule here invites exactly the mechanical score-blending the architecture creative rejected when it killed the RRF fusion module.

Constraints:

- Consistent with the siblings' shipped "Relaying to a human" posture: the agent is the tool's operator, not its display; it answers in natural language and hands raw output only on request.
- No score arithmetic across surfaces — similarity scores are relative within one query; SQL rows have none. Any "fused ranked list" implying a shared numeric ordering would be dishonest.
- Context-truncated presentation (the phase's headline), leaning on the siblings' existing `--detail` discipline rather than new mechanism.
- Litter constraint: the rule must be short, actionable prose — no fusion theory.

## Options Evaluated

- **Option A — Fused ranked list**: `sr-search` always produces one merged, ranked result list across whatever surfaces ran.
- **Option B — Narrated answer only**: `sr-search` always answers in prose, citing the supporting hits; never presents a list artifact.
- **Option C — Narrated answer by default; judgement-ordered list on request**: prose answer citing evidence is the default grain; when the user's ask is inherently a list ("show me the sessions about X"), present one merged list ordered by the agent's relevance judgement, deduplicated by id, never by blended scores.

## Analysis

| Criterion | A — fused list | B — narrated only | C — narrated default, list on request |
|-----------|----------------|-------------------|----------------------------------------|
| Honest about incomparable orderings | ✗ implies a cross-surface ranking that doesn't exist | ✓ | ✓ list order is stated judgement, not fake math |
| Consistent with sibling posture | ✗ siblings explicitly say "don't paste raw output at a human" | ✓ | ✓ same posture, extended |
| Fits list-shaped asks | ✓ | ✗ contorts "show me the sessions" into prose | ✓ |
| Simplicity of the prose rule | ~ needs a merge algorithm in prose | ✓ | ✓ one default + one exception |

Key insights:

- Option A is the RRF fusion module reborn as prose — the architecture creative's core finding ("the router was dumb because it was in the wrong layer") applies equally to ranking: mechanical fusion in *any* layer is the mistake.
- The dedup key already exists and is uniform: `message_id` / `(harness, session_id)`. When both surfaces return the same row, it is one piece of evidence found two ways — which is a *relevance signal*, not a conflict.

## Decision

**Selected**: **Option C** — narrated answer citing its evidence by default; a single merged, judgement-ordered list when the ask is list-shaped. Dedup across surfaces by `message_id`/`session_id`; a hit surfaced by both routes is a strong-relevance signal. Never blend or compare scores across surfaces.

**Rationale**: Matches the siblings' relaying posture and the question-shaped reality (some asks are answers, some are lists) while keeping the merge rule honest — ordering by stated judgement instead of fabricated cross-surface math — and short enough to satisfy the litter constraint.

**Tradeoff**: No deterministic, reproducible ranking for the both-surfaces case. Accepted: routing and synthesis are prompt-driven judgement by design; determinism lives in the sibling surfaces.

## Implementation Notes

- The synthesis section states: default grain (prose answer citing hits), the list-on-request exception, the id-based dedup rule with the found-both-ways signal, and the no-cross-surface-score rule — each as one actionable line.
- Truncation guidance delegates: scan at the siblings' default `snippet` detail, fetch full text per the `sr-semantic` → `sr-query` handoff the siblings already document.
