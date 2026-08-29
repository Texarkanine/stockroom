# Progress

Put a visual warehouse schema (ERD or equivalent) in the `sr-query` skill and in human docs, derived from the migration chain, with a generator local developers can run and a CI check that fails on drift. Technique is secondary to those two properties; prefer avoiding a dummy DuckDB if something equally faithful exists. See `memory-bank/active/projectbrief.md`.

**Complexity:** Level 3

## 2026-08-29 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - Validated intent against issue #127 plus operator refinements on generator elegance, CI drift, and no localdev install requirement
    - Classified as Level 3 (intermediate feature: skill + docs + generator + CI; design choices on how to derive the ERD)
* Decisions made
    - Dummy-database generation is acceptable only if no equally faithful lighter technique exists
    - Committed-layout-equals-install stands: skill resource is committed, not generated on main after install
* Insights
    - `sr-query` already tells agents to introspect `information_schema` and keeps a prose column sketch "as of migrations 0001–0008"; the human blocker is a visual, not agent rediscovery
    - Architecture (`docs/architecture/warehouse.md`) deliberately does not list DDL; the new visual should not dump DDL into Architecture

## 2026-08-29 - PLAN - COMPLETE

* Work completed
    - Mapped components: schema goldens, stdlib generator, sr-query skill, Advanced docs symlink, engine pytest, Make/CI
    - Wrote TDD-ordered implementation plan (9 steps) in `memory-bank/active/tasks.md`
    - Confirmed no open questions; skipped creative
* Decisions made
    - Derive the ERD from the head `NNNN_snapshot.json`, not a dummy warehouse
    - Logical relationships are an explicit list in the generator (DuckDB has no FOREIGN KEYs by design)
    - Empty-PK snapshot entities are drawn as views (`session_token_usage` already lives under `tables` in the golden)
    - Dual-audience SSOT under `skills/sr-query/references/`; docs Advanced symlink (cookbook pattern)
    - Architecture only routes to the picture; SKILL drops the hand-maintained column catalog
* Insights
    - Head golden already includes all six queryable names including the token VIEW; extending `_introspect_schema` is unnecessary
    - Cookbook symlink tests are the right contract shape; do not add SKILL.md phrase change-detectors
