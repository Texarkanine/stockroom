# Milestones: p2-embeddings-search

## Cross-milestone invariants & constraints

Properties every sub-run must preserve, regardless of which milestone it implements:

- **No truncation at rest.** Embeddings derive from whole stored content via bounded chunks fed to the model; the full text stays in the warehouse untouched. Truncation is a **read-time** concern only. No milestone may cap, trim, or drop stored content.
- **Storage and embedding stay decoupled.** Full text lives in the store; only bounded chunks reach the model, so a 200 KB field never threatens the embedder.
- **Torch-safe contract (Phase 0).** Embedding work runs on the torch exception; **never run an exact sync** (`uv run --no-sync` / `--inexact`). `sentence-transformers` enters the lock via `make lock`; torch never does.
- **Locked-uv trust.** No new runtime dependency enters without a hermetic `make lock`.
- **Read surfaces open `read_only=True` through the `warehouse.open()` chokepoint** and let DuckDB reject writes — no app-level statement allow/deny-list.
- **Incremental, not from-scratch.** Re-embedding processes only new/changed content.
- **Schema changes only via new forward-only numbered migrations**, with the golden schema snapshot updated as a conscious, reviewed act.
- **Harness-labeled and cross-harness by default.** A search is cross-harness by omitting the `harness` column, per-harness by filtering it.
- **Clean-room boundary.** Search/embedding/index logic is reimplemented from the briefs/spike and first principles — not ported from `cursor-warehouse`.
- **Test-first + green `make ci` for Python.** The TDD rule binds all **Python** work (the engine modules + the truncation mechanism). **Prompt-skill behavior is verified artisanally** by the operator (manually exercising routing + behavior); per-harness invocation forms are verified in Phase 5.

### Search-surface architecture (added 2026-06-29 — see `creative-search-surface-architecture.md`)

- **Python surfaces are power-user superpowers; `sr-*` skills are their safe LLM wrappers.** The engine modules (`stockroom.query`, `stockroom.semantic`, …) are the raw, full-power surfaces. Each `sr-*` skill is the *one place* that encodes how an LLM uses its surface safely and ergonomically — truncation handling, guardrails against context blowout and wasted tool calls, helper `scripts/`. Operational knowledge lives once, in the wrapper.
- **`sr-search` is judgement, not a primitive.** It is an LLM-judgement skill that routes a question to keyword/SQL (the **`sr-query` skill**), semantic (the **`sr-semantic` skill**), or both, then merges/ranks and presents. There is **no `stockroom.search` fusion module** and no hard-coded blend — routing and synthesis are prompt-driven, and `sr-search` **delegates to the sibling skills** (not the engine modules directly) so per-surface advice is never duplicated.
- **Read-time truncation is a tested Python mechanism on the read surfaces** (not LLM discretion): demonstrable + test-first, bounding output to a context-safe size with the full content preserved at rest. The skills expose and advise on it; the LLM chooses the level.

## Mid-flight realignment (2026-06-29)

After m1 + m2, planning the original third milestone ("`sr-search` — a Python blended keyword + semantic entrypoint with RRF fusion") surfaced an architectural error, corrected here with the operator (nothing has shipped; realignment is cheapest now). Two findings drove it:

1. A Python keyword path **duplicates `sr-query`** (raw SQL already does `ILIKE`), and a Python router can only be a dumb always-blend — the *intelligent* "plain query vs. semantic vs. both" decision is an **LLM judgement**, not a heuristic.
2. The `sr-*` skill wrappers were wrongly deferred wholesale to Phase 5. `sr-search` is itself a skill that must **leverage the `sr-query` / `sr-semantic` skills**, so those must exist first — and the wrappers are the single home for the operational advice (truncation, guardrails) that keeps an LLM safe on the power-user surfaces. Phase 5 keeps only the empirical **per-harness invocation-form** verification.

The remaining work is therefore re-decomposed into four sequential milestones (below). The prior m3 plan and its creative docs (`creative-keyword-search-mechanism`, `creative-search-routing-and-fusion`, `creative-read-time-truncation`) are **superseded** and removed; the decision record is `creative-search-surface-architecture.md`.

## Execution Order

Strictly sequential; each builds on verified artifacts from the prior. m1 (embedding pipeline) and m2 (`sr-semantic` engine module) are complete. The four remaining milestones land truncation first (the headline feature + a prerequisite the wrapper skills advise on), then the two power-user wrapper skills, then the judgement skill that composes them.

- [x] **Embedding pipeline** — VSS/HNSW index migration (`0003`, cosine, experimental persistence) + a `sentence-transformers` (`bge-small-en-v1.5`, 384-dim) embedder with chunking, device selection, `FLOAT[384]` writes through the chokepoint, and incremental re-embed.
- [x] **`sr-semantic` engine module** — `stockroom.semantic`: embed the query, cosine KNN over the HNSW index, over-fetch + max-sim owner dedup, owner join, ranked read-only output. (The *module*; its safe skill wrapper is a milestone below.)
- [ ] **Read-time output truncation** — a shared, tested read-time output-truncation mechanism (bound wide output to a context-safe width with a visible elision marker; selectable detail levels, e.g. `compact | snippet | full`) wired into `stockroom.query` and `stockroom.semantic` rendering. Full content stays whole at rest — the Phase-2 headline "truncation is a feature", as tested Python.
- [ ] **`sr-query` skill** — author the `sr-query` SKILL.md wrapping `python -m stockroom.query`: ergonomic, safe LLM guidance for read-only SQL (when/how to use it, the truncation flags, guardrails against context blowout & wasted tool calls) + any helper `scripts/`.
- [ ] **`sr-semantic` skill** — author the `sr-semantic` SKILL.md wrapping `python -m stockroom.semantic`: ergonomic LLM guidance for pure vector search (query phrasing, `-k`, detail/truncation, guardrails) + any helper `scripts/`.
- [ ] **`sr-search` skill** — author the `sr-search` SKILL.md: the friendly default that uses LLM judgement to route a question to keyword/SQL (via the `sr-query` skill), semantic (via the `sr-semantic` skill), or both, then merges/ranks and presents a context-truncated answer. No Python fusion module; delegates to the sibling skills.

## Scope estimates & rationale

Advisory only — the actual classification happens at the start of each sub-run.

- **Read-time output truncation — est. L2.** A contained, additive mechanism on two existing renderers, test-first, no schema/migration. Could be L1 if a single shared helper with thin wiring suffices, or tip to L3 if "context-aware" warrants a real budgeting design (a creative).
- **`sr-query` skill — est. L1/L2.** A prose SKILL.md (+ optional helper `scripts/`) wrapping an existing module; small and contained — mostly authoring + artisanal verification.
- **`sr-semantic` skill — est. L1/L2.** As above, for the semantic surface.
- **`sr-search` skill — est. L2/L3.** The judgement/orchestration skill: routing-prompt design, delegation to the sibling skills, synthesis/ranking, truncation guidance. The meatiest of the four; a creative on the routing/synthesis prompt may be warranted.

## Open questions for the sub-runs (advisory)

Not blockers — flagged so the right sub-run resolves each deliberately:

- **Truncation default posture for `sr-query`** — on-by-default (with a `--full` escape) or off-by-default for the power-user SQL surface? Resolve in the truncation milestone.
- **One wrapper-skill milestone or two** — `sr-query` and `sr-semantic` skills are near-identical thin wrappers; kept separate here per the operator's stated `sr-query → sr-semantic → sr-search` order, but a sub-run may merge them if the duplication proves trivial.
- **`sr-search` synthesis grain** — a fused ranked list, a narrated answer, or both? And does it delegate by *invoking the sibling skills' commands* or by *following their guidance inline*? Resolve in the `sr-search` skill milestone (likely a creative).
- **Skill packaging mechanics** — front-matter (`enable-model-invocation`), the plugin-root resolution + torch-safe invocation contract (already in `systemPatterns.md`), and where helper `scripts/` live. Resolve when authoring the first wrapper skill.
