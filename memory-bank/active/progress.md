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

## 2026-08-29 - PREFLIGHT - COMPLETE

* Work completed
    - Validated the 9-step plan against the checkout: golden shape/head discovery, PK-based view heuristic, Mermaid support, cookbook symlink precedent, Make-from-pytest precedent, CI job working-directory, REUSE overrides, absence of blocking enumeration tests
    - `.preflight-status` first line: `FAIL (fixable)`
    - TDD Plan Encoding: PASS (units 1-4 order tests before code; no change-detectors; no in-phase `tasks.md` edits needed)
* Decisions made
    - Two fixable gaps must be resolved in-plan before Build: (1) `scripts/gen_warehouse_schema.py` falls outside the only Python lint/format lane (ruff runs with cwd `skills/sr-search`, no root ruff config, no pre-commit) - extend `lint`/`format-check` in the Makefile step already in scope, or relocate the generator; (2) the generated body must be link-free because the same bytes are served from both the skill path and the docs symlink path
* Insights
    - View heuristic is provably safe today, not just asserted: `session_token_usage` is the only empty-PK entity; `embeddings` carries a 4-column PK
    - `docs/advanced/.pages` has no `- ...` wildcard (the cookbook one does) and properdocs is `strict` with `omitted_files: warn`, so the nav entry must land with the symlink, not four steps later
    - `STOCKROOM_UPDATE_SCHEMA_GOLDEN` is documented nowhere in `docs/`, so step 8 writes a new section rather than appending to an existing owner
    - Advisory offered: replace the hand-maintained `RELATIONSHIPS` constant with `-- @rel` declarations in the migration SQL plus a coverage assertion, retiring the plan's only accepted-drift item

## 2026-08-29 - PLAN - COMPLETE (replan after FAIL (fixable))

* Work completed
    - Folded both fixable gaps and the cheap advisories into `tasks.md`
    - Deferred `@rel` coverage to a follow-up (six-entity overlay is enough for this task)
* Decisions made
    - Keep the generator in `scripts/`; extend `lint` / `format` / `format-check` with `$(UV_RUN) ruff … ../scripts`
    - Generated markdown is link-free; a unit test asserts it; human cross-links stay on single-path pages
    - Add Advanced `.pages` nav in the same step as the symlink (strict omitted_files)
    - Step 8 is a new engine.md section, not an append to a nonexistent golden-update owner
* Insights
    - Cookbook recipe bodies already have zero markdown links for the same dual-path reason; the agent index is not symlinked and may link
    - `UV_RUN` cwd is the engine dir, so `../scripts` is the correct ruff path (reuse-style root invocation is unnecessary)
