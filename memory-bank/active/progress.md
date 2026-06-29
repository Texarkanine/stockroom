# Progress

Milestone 3 of the Phase 2 (`p2-embeddings-search`) L4 project: **`sr-search`** — the
blended keyword + semantic entrypoint. Route an incoming question to SQL / vector / blend,
run keyword search and (reusing m2's `stockroom.semantic`) semantic search, merge and rank
the two result sets, and apply a context-aware **read-time truncation** level so a huge
field never floods the caller's context. Follows the Phase 1 / m2 engine-module precedent
(`python -m stockroom.search`); the polished skill wrapper + per-harness invocation stay
deferred to Phase 5. Cross-milestone invariants from `milestones.md` remain binding
(read-only chokepoint, **no truncation at rest** — truncation is read-time only,
harness-labeled/cross-harness by default, torch-safe contract, clean-room boundary,
test-first + green `make ci`).

**Complexity:** Level 3

## 2026-06-29 - COMPLEXITY ANALYSIS - COMPLETE

* Work completed
    - Advanced the L4 milestone tracker: marked m2 (`sr-semantic`) `- [x]`, deleted the m2 sub-run ephemeral files (`tasks.md`, `activeContext.md`, `progress.md`, `.qa-validation-status`, `.preflight-status`); preserved `milestones.md`, `projectbrief.md`, and `reflection/`.
    - Classified the third milestone (m3 — `sr-search`) as **Level 3 (Intermediate Feature)**.
    - Created the m3 sub-run ephemeral files (fresh `progress.md`, `activeContext.md`, `tasks.md` stub).
* Decisions made
    - L3, not L2: m3 is a complete feature composed of multiple cooperating components — a query router (SQL / vector / blend), a keyword-search mechanism, rank fusion across two result sets, and the headline context-aware read-time truncation — and carries genuine open design decisions (DuckDB FTS vs. `LIKE`/regex, the fusion algorithm, the truncation-level scheme) that warrant a creative phase. Consistent with the milestone's advisory L3 estimate.
* Insights
    - Unlike m1/m2 (contained, mechanism-reuse work), m3 is where the design surface lives: it composes the proven m1 embedder + m2 semantic surface with new routing/fusion/truncation logic, so the load-bearing risk is in the design choices, not the wiring.

## 2026-06-29 - CREATIVE - COMPLETE (3 explorations, all high-confidence)

* Work completed
    - Opened with a throwaway probe of the one load-bearing unknown (the keyword mechanism), per the m1/m2 "spike load-bearing primitives first" lesson: DuckDB 1.5.4 → `ILIKE` is built-in and correct; `fts` is **un-bundled** (needs a network `INSTALL`) and `create_fts_index` materializes a **stale-on-insert** stored schema (a write).
    - `creative-keyword-search-mechanism.md` (architecture) → **`ILIKE`** over FTS.
    - `creative-search-routing-and-fusion.md` (architecture) → **blend-by-default** + `--mode` (no auto-router; resolved the NL→SQL scope trap by collapsing "SQL" to the keyword path), fused with **Reciprocal Rank Fusion**.
    - `creative-read-time-truncation.md` (algorithm) → **discrete detail levels** `compact|snippet|full` (default `snippet`), per-result cap, trim only in the render path.
* Decisions made
    - The keyword decision **forced** the fusion choice: `ILIKE` yields no score, so rank-based RRF (not weighted-score fusion) is the natural fit, with the semantic cosine ranking carrying relevance weight.
    - `--harness` (m2's deferred per-harness filter) is implemented as **one additive, backward-compatible** param on `run_semantic_search` (filter inside the KNN), the only m2 touch.
    - Total-output `--budget` truncation deferred as a future enhancement (YAGNI for v1).
* Insights
    - The probe converted the single biggest design risk into a settled, evidence-backed decision before any code — the keyword/fusion/truncation trio then fell out coherently (each decision constrained the next). No low-confidence outcomes, so no operator gate inside creative.

## 2026-06-29 - PLAN - COMPLETE

* Work completed
    - Wrote the full L3 plan to `tasks.md`: component analysis (new `stockroom.search`, one additive `semantic` change, no schema/migration), the resolved open questions, a pinned data-flow diagram, a ~30-behavior TDD plan, 8 dependency-ordered test-first steps, challenges, and technology validation.
* Decisions made
    - **No new technology / no migration** — purely additive engine + test code (the m2-like profile), so technology validation is a no-op beyond the keyword probe already done.
    - Engine-module precedent (`python -m stockroom.search`, `run_search` + `con`/encoder injection, `main`+`encoder_factory`); polished skill wrapper deferred to Phase 5.
    - Keyword-only mode needs **no torch** (encoder built lazily only when semantic runs) — a genuine ergonomic win and a clean torch-free CLI test.
* Insights
    - m3 is the most logic-heavy Phase-2 milestone but still a single coherent surface (one module, no independent workstreams) — confirmed L3, not L4. The contrast with m1/m2 is the design density, not the integration surface.
* Next step
    - 🧑‍💻 Plan is complete; the next L3 phase (Preflight) is operator-initiated. Run `/niko-preflight` to validate the plan against codebase reality before build.
