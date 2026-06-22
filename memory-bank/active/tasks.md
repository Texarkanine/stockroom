# Tasks — Stockroom Planning

## Document Pipeline

- [x] Research the references (`cursor-warehouse`, `claude-warehouse`, `slobac`) and uv supply-chain behavior
- [x] Collect and resolve scope-defining questions with the operator (two rounds)
- [x] Draft the brainstorm (`planning/brainstorm/`: README + product + tech + roadmap + implementation-details)
- [x] Seed this memory bank for window-close continuity
- [x] Operator finalized scope + resolved Open Items (O1–O15, all except the O9 torch spike); brainstorm committed
- [x] Author the Product Brief (`planning/product-brief.md`) and verify
- [ ] Author the Tech Brief (`planning/tech-brief.md`), closing the torch spike (O9), and verify ← current gate
- [ ] Author the Roadmap (`planning/roadmap.md`) and verify
- [ ] Retire the brainstorm; promote design docs into persistent memory-bank context when build starts

## Open Items

Full resolution table at `planning/brainstorm/README.md`. **O1–O15 are resolved except O9.**

- [ ] **O9 — torch packaging mechanism ("lock everything except torch").** The one genuinely-open item: an empirical `uv` spike, not a decision. Executed when authoring the Tech Brief; gates embedding work.
- [x] O1, O3–O8, O10–O15 — resolved (see README). Notably: O12 → **v1 ingests both Cursor + Claude Code**; O10 → no raw layer; O13 → read-time truncation only.
- [ ] Migration lock primitive on DuckDB (advisory table vs file lock) — an implementation detail to settle during the migration build, not a scope decision.
