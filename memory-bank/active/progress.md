# Progress

Milestone 1 of the Phase 2 (`p2-embeddings-search`) L4 project: the **embedding
pipeline**. Land the deferred VSS/HNSW cosine index as a new forward-only
migration (`0003`, experimental persistence on so deletes work against a live
index), build a local `sentence-transformers` (`all-MiniLM-L6-v2`, 384-dim)
embedder with chunk-and-mean-pool and GPU-or-CPU device selection, and write
`FLOAT[384]` vectors through the `warehouse.open()` chokepoint — re-embedding
only un-embedded/changed content. Built on the Phase 0 torch contract and the
Phase 1 warehouse. Binding sub-run findings live in `milestones.md` (torch-free
embedder testability, offline VSS provisioning, `owner_id` grain, the `0003`
migration-head ripple, and a mandatory load-bearing-primitive spike).

**Complexity:** Level 3

## 2026-06-28 - COMPLEXITY ANALYSIS - COMPLETE

* Work completed
    - Classified the first unchecked milestone (m1 — embedding pipeline) as **Level 3 (Intermediate Feature)**.
    - Created the m1 sub-run ephemeral memory-bank files (fresh `progress.md`, `activeContext.md`, `tasks.md` stub); preserved the L4 `projectbrief.md` and `milestones.md`.
* Decisions made
    - L3, not L4: the decision tree's "architectural implications" question is satisfied at the *Phase 2 L4 plan* level; within this sub-run the architecture is settled and the remaining unknowns (VSS provisioning, index persistence, `owner_id` grain) are resolved in a creative/spike phase — the L3 hallmark. Consistent with the preflight bound (each milestone ≤ L3) and the advisory L3 estimate.
* Insights
    - The preflight directive to open with a load-bearing-primitive spike (offline `vss`, HNSW cosine + live-delete persistence, CPU `all-MiniLM-L6-v2` encode) maps cleanly onto the L3 creative/exploration phase.

## 2026-06-28 - CREATIVE - COMPLETE

* Work completed
    - Ran the mandated load-bearing-primitive spike against DuckDB 1.5.4 on this machine: `vss` INSTALL/LOAD OK; HNSW cosine KNN correct; DELETE/INSERT against a live index + survive-reopen OK with experimental persistence; `LOAD/SET/CREATE INDEX USING HNSW` run inside the runner's `BEGIN/COMMIT` and on `:memory:`. Confirmed `INSTALL` is the network op (`REPOSITORY` mode), `LOAD` is offline-safe. The CPU encode leg was already proven in `planning/spikes/o9-torch/` (torch absent here by design — not re-run).
    - Resolved all 3 open questions (high confidence), each documented under `memory-bank/active/creative/`.
* Decisions made
    - **VSS provisioning/index**: thin `0003` (index only); chokepoint `ensure_vss(con)` LOADs + sets persistence on every open and centralizes the rare network `INSTALL`; fixtures call `ensure_vss` before the real chain. Keeps `INSTALL` off the runtime hot path while keeping the index a migration.
    - **Owner grain**: messages only for m1 (`owner_id=message_id`, `chunk_index=0`); `tool_calls` deferred (additive later via the existing `owner_table`).
    - **Incremental**: select owners lacking a current-`embed_model` vector (new + model change) + session-grained embedding cascade-delete in `ingest.writer` (edits), no schema column.
* Insights
    - The schema's `owner_table` and the per-connection persistence SET both pointed at the same architecture: defer breadth (messages-only), and make the chokepoint own `vss` loading since it already owns the migration gate and per-connection setup.

## 2026-06-28 - PLAN - COMPLETE

* Work completed
    - Wrote the full L3 plan to `tasks.md`: component analysis (4 engine modules + a bounded test-infra ripple), two pinned diagrams (data flow, torch-free test seam), TDD test plan (~14 behaviors + 2 integration), a 7-step ordered implementation plan, technology validation, and challenges/mitigations.
* Decisions made
    - Implementation order is dependency-led: pure chunker → injected-encoder pipeline (torch-free) → `ensure_vss`+`0003`+golden → head-version ripple → writer cascade → real-model encoder+CLI (torch-gated) → docs.
    - No `uv.lock` change (vss is a DuckDB extension, not a Python dep); torch stays out of the lock; CI stays torch-free.
* Insights
    - The migration-head bump is the one test-suite-wide event; the coupled assertions are a small, enumerated set (`test_migrate_runner`, `test_warehouse_open`) plus a new `0003_snapshot.json` — exactly as the Phase-1 reflection predicted.

## 2026-06-28 - PREFLIGHT - COMPLETE

* Work completed
    - Validated the implementation plan against codebase reality: **PASS (with advisory)**; wrote `.preflight-status`.
    - Caught and fixed a blocking **TDD-plan-encoding** gap: the test-first cycle was stated only in the plan preamble. Restructured all 7 steps with explicit (a) test-first / (b) implement substeps so the plan cannot be followed code-first.
    - Verified convention compliance (module/migration/snapshot precedents), the enumerated migration-head ripple, no conflicts, and requirement completeness.
* Decisions made
    - Folded the radical-innovation finding (an `--full` re-embed flag mirroring `ingest --full`) into step 6 — small, in-scope, precedent-aligned.
    - Recorded two build-time advisories: verify `ensure_vss`'s `SET`/`LOAD` succeed on read-only connections (m2 readers need vss); make the `0003` golden capture an index section since columns are unchanged from `0002`.
* Insights
    - The lone blocking risk was plan *encoding*, not design — the spike + creative had already de-risked the substance, so preflight's value here was forcing per-unit test-first rigor before the build gate.

## 2026-06-28 - PLAN AMENDMENT (operator-directed, at build gate) - COMPLETE

* Work completed
    - Queried the operator's real warehouse to ground two design questions: 27,282 messages (21,849 non-empty), median 167 chars, p95 4,811, **max 202,255**; ~75% single-chunk, 25% multi-chunk, ~48 K chunks total.
    - Added two creative docs and amended the plan per operator decisions: **per-chunk storage** (`creative-chunk-storage-grain.md`) and **`BAAI/bge-small-en-v1.5`** as the embedding model (`creative-embedding-model-selection.md`, grounded in current 2026 MTEB).
* Decisions made
    - **Per-chunk rows** (`chunk_index = 0..N-1`), max-sim dedup deferred to m2 — lossless, best long-tail recall, no schema change; supersedes the tech-brief's "one vector per source item." Updated `creative-embedding-owner-grain.md` accordingly.
    - **Model = bge-small-en-v1.5** over all-MiniLM-L6-v2: same 384-dim (no migration), +9 MTEB retrieval, 512-token window (2×, helps the long tail), no `trust_remote_code`, MIT; m1 passages need no prefix.
    - Chunk size raised to ~1200/150 (conservative proxy for the 512-token window); flagged token-aware tightening if dense-code chunks exceed 512 tokens.
* Insights
    - The "why 384?" question surfaced the real lever: 384 is a *model property*, not a knob; staying at 384 preserves model-upgrade freedom without a migration. And "are all chunks embedded?" correctly exposed mean-pool's dilution on the long tail — per-chunk storage is strictly more information (you can pool at read time; never the reverse).
    - The amendment changed *design*, not scope or complexity (still L3, still messages-only, still the same components) — so it re-validates against preflight without a re-architecture.

## 2026-06-28 - SPIKE: empirical embedding-model eval - COMPLETE (decision open)

* Work completed
    - Operator has torch provisioned locally (GTX 1070, CUDA 12.6). Built a real known-item retrieval benchmark on the operator's own corpus: query=user turn, gold=the assistant reply (`parent_id` edge), pool=14,472 assistant messages; 2,110 labeled pairs. Metrics: MRR@10, Recall@{1,5,10}, mean/median rank, + GPU/CPU throughput. Spike at `planning/spikes/embed-model-eval/` (README + export_dataset.py + benchmark.py + results.json; parquet gitignored — private text).
    - Provisioned `sentence-transformers` into the torch interpreter (reused existing torch). Fixed a gte-small hang (no native max_seq_length → tried to encode a 202k-char query); capped every model to its native window.
* Results (MRR@10 / R@1 / CPU-per-s): e5-small-v2 0.266 / 0.216 / 10; gte-small 0.245 / 0.174 / **1**; bge+prefix 0.239 / 0.178 / 11; bge no-prefix 0.204 / 0.151 / 8; MiniLM 0.192 / 0.137 / 23.
* Findings
    - **MiniLM is clearly weakest on quality** (last on every metric, large consistent gap) — switching off it is empirically confirmed.
    - **bge query prefix is worth +0.035 MRR** (0.204→0.239) — m2 should use it if bge is chosen.
    - **gte-small disqualified** by CPU throughput (1/s ≈ 13 h cold-embed) despite best median rank.
    - **Empirical winner ≠ MTEB desk pick:** e5-small-v2 (lowest MTEB of the set) tops R@1/MRR here — the "evaluate on your own corpus" lesson. Its cost is the mandatory dual `passage:`/`query:` prefix (footgun across m1/m2).
* Decision (OPEN — operator's call)
    - Narrowed to **e5-small-v2** (best top-1, fast, dual-prefix contract burden) vs **bge-small-en-v1.5+prefix** (simpler/lower-footgun contract, MIT, no passage prefix, a hair less R@1). Both decisively beat MiniLM. Plan currently encodes bge; flip to e5 is a one-line EMBED_MODEL + prefixes, no schema change (still 384-dim).

## 2026-06-29 - SPIKE: cross-corpus generalization check - COMPLETE (decision RESOLVED → bge)

* Work completed
    - Made the benchmark portable (CUDA→MPS→CPU, single-env, direct DB open, `--label`); pushed to branch `spike/embed-model-eval` and cherry-picked onto `initialdev`. Operator ran it on a **second, independent corpus** — their MacBook's Cursor/Claude history (Apple-Silicon MPS) — to test whether the ranking generalizes beyond the Linux corpus.
* Results — corpus B (MacBook), 15,775 passages / 2,185 pairs (MRR@10 / R@1): e5 0.252 / 0.196; gte 0.235 / 0.168; bge+prefix 0.223 / 0.161; bge no-prefix 0.186 / 0.131; MiniLM 0.177 / 0.125.
* Findings
    - **Model ordering is IDENTICAL across both corpora** (`e5 > gte > bge+prefix > bge no-prefix > MiniLM` on MRR@10 and R@1). Absolute scores ~0.01–0.015 lower on B, but every relative gap holds. The operator's "is my corpus representative?" worry is answered: **the ranking is not a one-corpus artifact.**
    - bge query-prefix lift reproduces (+0.037 MRR on B vs +0.035 on A). MiniLM last on both. gte's faster Mac CPU number is just a faster host CPU — still ~8× slower than peers, so the commodity-Linux-CI disqualification stands.
* Decision (RESOLVED — operator)
    - **`bge-small-en-v1.5`** confirmed for m1 (the plan already encodes it). e5's small, consistent top-1 edge doesn't outweigh bge's simpler/robust prefix contract (no passage prefix; m2 query-prefix optional, gain captured). Escape hatch unchanged: switching to e5 later is a one-line `EMBED_MODEL` + dual prefixes, no schema change. **Embedding-model exploration is closed.**

## 2026-06-29 - BUILD - COMPLETE

* Work completed
    - Implemented all 7 plan steps strictly test-first, dependency-ordered, in three feature commits + a docs commit. New `stockroom.embed` (chunker, `Encoder` protocol, `embed_chunks`, `embed_pending`, `BgeEncoder`, `python -m stockroom.embed [--full]` CLI); `warehouse.ensure_vss` wired into `open()`; thin migration `0003` (cosine HNSW index) + cumulative `0003_snapshot.json` with an indexes section; embedding cascade-delete in `ingest.writer`.
    - Migration-head ripple 2→3 across `test_migrate_runner`, `test_warehouse_open` (repointed to 0003 snapshot + `{tables,indexes}` introspection), and `test_warehouse_concurrency` (a plan under-enumeration, fixed in scope). Added `test_open_reader_has_vss_loaded`.
    - `make ci` green: **202 passed, 1 torch-gated skip**; lock-check clean (**no `uv.lock` change**); ruff + REUSE clean. Verified an end-to-end ingest→embed→KNN→re-ingest-cascade→re-embed smoke on the real fixture corpus (40 msgs → 38 chunk vectors; nearest == queried; cascade to 0 then back to 38).
* Decisions made
    - **Owner-replacement on (re)embed:** the `embeddings` PK excludes `embed_model`, so coexisting models would collide at the same `chunk_index`; `embed_pending` deletes a selected owner's prior rows before inserting (incremental selection unchanged). Corrected a test that wrongly expected two models to coexist.
    - **`ensure_vss` runs on every connection (RW + RO):** probe + `test_open_reader_has_vss_loaded` confirmed `LOAD`/`SET …persistence` succeed on read-only handles — the read-only advisory is resolved without writer-only scoping.
    - **0003 golden locks name/table/`expressions`;** the cosine metric (not introspectable via `duckdb_indexes()`) is verified functionally by the KNN test.
    - **CLI testability seam:** `main(..., encoder_factory=BgeEncoder)` keeps the CLI testable torch-free; `BgeEncoder` is the lone `importorskip`-gated edge.
* Insights
    - The single load-bearing surprise was a schema fact, not a design gap: the `embeddings` PK's exclusion of `embed_model` makes "replace on re-embed" the only consistent behavior — exactly the kind of thing the test-first pass surfaces before it becomes a latent dup-key bug. Everything else (vss, HNSW persistence, RO load, head ripple) had been pre-de-risked by the spike + preflight, so the build was friction-light.

## 2026-06-29 - QA - COMPLETE (PASS)

* Work completed
    - Semantic review of the built code against the plan + 5 creative docs across KISS / DRY / YAGNI / Completeness / Regression / Integrity / Documentation. No substantive findings; two trivial fixes applied directly and re-verified.
    - Fixes: (1) **YAGNI** — removed an unused `@runtime_checkable` decorator (no `isinstance` use) and its import; (2) **Documentation** — corrected `embed_pending`'s `--full` docstring (it deletes *all* of an owner's message rows, not just current-model). Re-ran `make ci`: green (202 passed, 1 torch-gated skip; ruff + REUSE clean; no lock change). Status file at `memory-bank/active/.qa-validation-status`.
* Decisions made
    - Kept the `Encoder` `Protocol` (the lone abstraction) — it's a documented torch-free testability seam, not gratuitous indirection, so it survives YAGNI.
    - Left the unconditional per-owner `DELETE` in `embed_pending`'s loop (a harmless no-op for brand-new messages) rather than special-casing — KISS over a micro-optimization on a write path.
* Insights
    - The build was clean enough that QA reduced to a lint-grade pass: the only two findings were a dead decorator and a one-clause doc drift. Test-first + preflight front-loaded the substantive risk, leaving QA to confirm rather than repair.
