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

## Test Plan (artisanal — TDD passes by project-invariant exemption)

The deliverable is prose with no Python; per the project invariant ("prompt-skill behavior is verified artisanally"), verification is operator-style live exercise plus the repo gate. Behaviors to verify, each mapped to a concrete check:

### Behaviors to Verify

Routing (verified by desk-checking the skill's routing section against these cases — the skill must classify each unambiguously):

- Exact/structured ask ("how many sessions per harness?") → route to `sr-query` alone.
- Meaning-based ask ("where did we debug the warehouse deadlock?") → route to `sr-semantic` alone.
- Ambiguous/broad ask ("find everything about REUSE licensing") → both surfaces, then synthesize.
- Known-id ask ("show me message X in full") → `sr-query` alone (the siblings' handoff pattern).

Delegation (creative: delegation-mode):

- The skill names the siblings and the relative-path fallback exactly once; grep-verifiable: no `APP_DIR`, no `PYTHONPATH`, no `uv run`, no `--no-sync`/`--no-config` anywhere in `skills/sr-search/SKILL.md`.

Synthesis (creative: synthesis-grain):

- Default grain is a narrated answer citing evidence; list-shaped asks get one merged judgement-ordered list; dedup by `message_id`/`session_id`; no cross-surface score blending. Verified by desk-check that each rule appears as one actionable line.

End-to-end (live, against the real warehouse — the operator's artisanal posture, m4/m5 precedent):

- One exact ask, one meaning ask, one both-surfaces ask executed live by following the skill as written (routing → sibling contract → synthesis), confirming the skill's instructions suffice without improvisation.

Litter audit (operator constraint):

- Final pass against `planning/brainstorm/skill-litter-audit.md` categories A–C: no rationale, no content doubled from the siblings, no narration/reassurance padding. The test for every sentence: "does the agent need this to act correctly or recover from failure right now?"

### Test Infrastructure

- Framework: none applicable to prose; the repo gate is `make ci` (pytest, ruff lint+format, lock-check, REUSE) — must stay green (no Python changes expected, so this is a regression gate).
- New test files: none.

### Integration Tests

- Sibling cross-references: `sr-query`/`sr-semantic` "that judgement belongs to the `sr-search` skill" lines resolve correctly against the rewritten skill (no edits expected; verify the read).
- `make localdev` mirror refresh; front-matter parses (three skills discoverable).

## Implementation Plan

1. ✅ **Rewrite front-matter** — `skills/sr-search/SKILL.md`
    - `enable-model-invocation: false → true`; description becomes the routing contract: the friendly default search over agentic-coding history; use it when unsure whether the question is exact/structured (`sr-query`) or meaning-based (`sr-semantic`), or when it needs both. Mirrors the siblings' routing-bearing description style.
2. ✅ **Body: judge → route** — same file
    - Replace the skeleton body. Open with what the skill does (one line), then the routing judgement: the exact/structured vs. meaning-based discriminators (reusing the siblings' own "when to use" cues by reference, not restatement), the both-surfaces case, and the known-id case.
    - Creative ref: `creative-sr-search-delegation-mode.md` — delegation is by sibling name with the single relative-path note; **no invocation section**.
    - *Preflight amendment:* the four routing desk-check cases from the test plan ship as the skill's own routing examples, so the verification cases and the shipped content are one artifact (the m4/m5 "every shipped example is verified" discipline, applied to routing).
3. ✅ **Body: synthesize → present** — same file
    - The four synthesis rules as actionable lines (default narrated grain; list-on-request; id-based dedup with found-both-ways signal; no cross-surface score math), plus truncation-by-delegation (scan at sibling defaults; full text via the siblings' documented handoff) and the relaying-to-a-human posture consistent with the siblings.
    - Creative ref: `creative-sr-search-synthesis-grain.md`.
4. ✅ **Engine-home note** — same file
    - One short line preserving the fact that this directory hosts the shared engine (developers: see the README / `systemPatterns.md`). The skeleton's entrypoint inventory and invocation block are deleted, not relocated — the siblings and the README already own that content.
5. ✅ **Litter pass** — same file
    - Category A–C sweep per the audit before verification; grep for the forbidden invocation tokens.
6. ✅ **Verification** — live warehouse + repo gate
    - Execute the end-to-end behaviors above; run `make localdev`; run `make ci` (restore torch via `make torch` if the CI sync strips it — m4/m5 precedent); verify sibling cross-references.

## Technology Validation

No new technology — validation not required (prose-only change; no dependencies, no build-tool or config changes).

## Challenges & Mitigations

- **Routing prose that sounds right but routes wrong**: desk-check against the four behavior cases; the live end-to-end pass catches improvisation gaps.
- **Litter creep via the m4/m5 template**: the siblings are the structural template but carry known Category A–C litter; copy structure, not sentences. The grep check and category sweep are explicit plan steps.
- **Losing the engine-home breadcrumb**: deleting the skeleton entirely could strand a developer landing in `skills/sr-search/` — mitigated by the one-line note (step 4).
- **`make ci` sync stripping torch**: anticipated; `make torch` restores (m4/m5 precedent).
- Not Level 4: single prose deliverable, no workstream decomposition needed.

## Status

- [x] Component analysis complete
- [x] Open questions resolved (2/2, both high confidence)
- [x] Test planning complete (artisanal)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Preflight (PASS)
- [x] Build
- [ ] QA
