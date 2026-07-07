# Progress

Sub-run m6 (final milestone) of the `p2-embeddings-search` L4 project: author the **`sr-search` skill** — the friendly-default SKILL.md that uses LLM judgement to route a question to keyword/SQL (via the `sr-query` skill), semantic (via the `sr-semantic` skill), or both, then merges/ranks and presents a context-truncated answer. No Python fusion module; it delegates to the sibling skills so per-surface operational advice lives once. Two design questions are deliberately deferred to this sub-run (see `milestones.md` open questions): the synthesis grain (fused ranked list, narrated answer, or both) and the delegation mode (invoke the siblings' commands vs. follow their guidance inline) — a creative phase on the routing/synthesis prompt is anticipated. Per the project invariant, prompt-skill behavior is verified artisanally; the TDD rule binds only any Python helper scripts.

**Operator constraint (2026-07-07):** avoid *littering* the new skill — apply the understand-vs-do split from `planning/brainstorm/skill-litter-audit.md` at authoring time. The skill carries task knowledge only (routing, incantation, flags, guardrails-as-actions, error→next-action); no Category A rationale, no Category B doubled content, no Category C narration/reassurance padding. The audit's sequencing note stands: m6 is authored against the *current* invocation contract (the on-path CLI lands later, Phase 4), so the fragile incantation itself is inherited — but nothing beyond it.

**Complexity:** Level 3

## 2026-07-07 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - L4 re-entry (Step 2a): m5 (`sr-semantic` skill) confirmed `REFLECT COMPLETE` and checked off in `milestones.md`; m5 sub-run ephemerals cleared (`tasks.md`, `activeContext.md`, `progress.md`, `.qa-validation-status`, `.preflight-status`). `creative/creative-search-surface-architecture.md` preserved (project-level decision record; m3.5/m4/m5 precedent).
    - Classified the **`sr-search` skill** milestone as **Level 3** and wrote the determination to the memory bank.
* Decisions made
    - Level 3, not Level 2: unlike m4/m5 (settled-design transcription of an existing CLI surface), m6 carries two unresolved design decisions (synthesis grain; delegation mode) that `milestones.md` explicitly routes to this sub-run "likely a creative" — and only the L3 workflow has a creative phase. It composes multiple components (routing across two sibling skills + synthesis + presentation) without architectural implications → decision-tree L3.
    - Operator constraint captured: author lean per the skill-litter-audit understand-vs-do split (task knowledge only; no rationale/duplication/narration litter), while still inheriting the current invocation contract per the audit's own sequencing.
* Insights
    - Standing insight carried from m4/m5 reflections: the engine run incantation is copy-pasted prose in N places; this milestone is the designated forcing point to *consider* a shared launcher — but the litter audit + `stockroom-on-path-cli.md` now route that fix to Phase 4 (`sr-initialize`), so m6 should inherit, not consolidate.
    - m5 reflection's standing insight (caught `ModuleNotFoundError` → clean stderr in `semantic.main()`) remains a candidate only if this milestone touches that module — it is not expected to.

## 2026-07-07 - CREATIVE (delegation mode) - COMPLETE

* Work completed
    - Explored the first m6 open question (how `sr-search` mechanically delegates to the sibling skills) as an architecture creative; wrote `creative/creative-sr-search-delegation-mode.md`; marked the question resolved in `tasks.md`.
* Decisions made
    - **Resolved (high confidence):** delegate by sibling skill *name* ("follow the `sr-query` / `sr-semantic` skill"), with one relative-path fallback note (`../sr-query/SKILL.md`, `../sr-semantic/SKILL.md`) for an agent holding only this file. Rejected: resolved-path file reads (reintroduces the plumbing the litter audit flags) and inlined commands (the duplication the architecture creative already rejected).
* Insights
    - The design moots the litter audit's "m6 temporarily inherits the invocation litter" concession: `sr-search` needs no invocation section at all — no `$APP_DIR`, no `PYTHONPATH`, no uv flags.
