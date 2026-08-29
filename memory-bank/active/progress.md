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
