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

## 2026-08-29 - PREFLIGHT - COMPLETE (re-run on revised plan)

* Work completed
    - Re-validated the revised 9-step plan against the checkout: confirmed both prior fixable gaps and both actionable advisories were folded into steps 1, 3, and 4; re-verified `Makefile` `UV_RUN` cwd, `docs/advanced/.pages` nav-wildcard absence, `scripts/`/`skills/sr-query/references/` non-collision, and the stale SKILL catalog line targeted for deletion
    - `.preflight-status` first line: `PASS WITH ADVISORY`
    - TDD Plan Encoding: PASS (fixes were folded into existing steps without breaking test-before-code ordering; no change-detectors; no in-phase `tasks.md` edits needed)
* Decisions made
    - No further plan changes required; proceed to Build
* Insights
    - The two remaining advisories (`sessions` ~24-attribute entity size; `@rel` migration-comment convention replacing the hand-maintained `RELATIONSHIPS` list) are operator-deferred, not new findings

## 2026-08-29 - PLAN - COMPLETE (fold in @rel)

* Work completed
    - Operator asked to take preflight's radical innovation; rewrote the edge source from a Python list to `-- @rel` / `-- @rel-none` in migrations plus coverage
    - Renumbered implementation to 10 steps (new executable unit: annotate 0001/0007)
* Decisions made
    - Grammar: `-- @rel from(cols) -> to(cols) [: label]` and `-- @rel-none entity`; child→parent draws `to ||--o{ from`
    - Coverage: every snapshot entity is from, to, or rel-none; names and column lists must exist on the snapshot; `@rel-none` cannot also be a from
    - `check()` runs coverage before comparing markdown
* Insights
    - Comments do not change DuckDB apply or golden JSON; the new gate is a regex over SQL the contributor already edits
    - `sessions` needs no `@rel-none` because it is a `<to>`

## 2026-08-29 - PREFLIGHT - COMPLETE

* Work completed
    - Re-validated the 10-step `@rel` plan against the checkout, including migrations, head golden, cookbook symlink precedent, Make targets, and the engine CI job
    - `.preflight-status` first line: `FAIL (fixable)`
    - TDD Plan Encoding passed; all executable units schedule tests before production changes
* Decisions made
    - Return to planning before Build to close the CI lint/format lane for the repo-root generator
* Insights
    - Root `make lint` and `make format-check` can cover `../scripts`, but CI currently invokes ruff directly from `skills/sr-search`, so the planned Makefile change alone does not enforce generator style in CI

## 2026-08-29 - PLAN - COMPLETE (CI ruff covers scripts/)

* Work completed
    - Step 6 now extends engine-job Lint / Format check to `ruff … . ../scripts` in addition to `make schema-docs-check`
* Decisions made
    - Do not replace CI ruff with `make lint` (would double-sync); pass `../scripts` on the existing uv ruff invocations
    - Declined this run's advisory (generated relationship-source appendix) unless asked
* Insights
    - `make schema-docs-check` is a content lockstep, not a Python quality gate

## 2026-08-29 - PREFLIGHT - COMPLETE

* Work completed
    - Re-validated the 10-step `@rel` plan against the checkout: confirmed the CI ruff-lane fix (unit 6) closes the prior `FAIL (fixable)`; grepped the full `migrations/` tree to confirm only `0001`/`0007` create tables/views (matches the plan's two-migration annotation scope); cross-checked head `0008_snapshot.json` PKs against the pinned `@rel` column lists and the empty-PK view heuristic; confirmed no existing ERD/schema diagram or `scripts/*.py` to conflict with
    - `.preflight-status` first line: `PASS WITH ADVISORY`
    - TDD Plan Encoding: PASS (units 1-5 order stub tests/interface before red tests before green code; prose/policy units 6-10 correctly carry no tests and no change-detectors; no in-phase `tasks.md` edits needed)
* Decisions made
    - No further plan changes required; proceed to Build
* Insights
    - `../scripts` has no ancestor `[tool.ruff]` config (root `pyproject.toml` is docs-only), so it lints under ruff defaults rather than the engine's `py311` pin - immaterial for stdlib code, noted as advisory only
    - Unit 3's field labeled `No tests: n/a — this step is executable` is a copy-paste leftover from the prose/policy template (the unit does schedule tests correctly) - cosmetic, not a TDD violation
    - Radical innovation offered (not applied): a sibling `-- @doc <column>: <description>` comment convention would let the generator absorb `sr-query`'s remaining hand-maintained column-meaning prose too

## 2026-08-29 - DECISION - @doc rejected

* Decisions made
    - Do not add `-- @doc`, and do not harvest inline `--` comments from the migration chain into generated docs
* Insights
    - Forward-only migrations are a write log. Prose a human must read cannot live there: an older file can still contain a string that a later migration made false, sitting next to strings that are still true
    - `@rel` is a different shape: coverage checks names against the *head* snapshot, so stale structural declarations fail; column essays would have to be merged across the chain and would not

## 2026-08-29 - BUILD - IN-PROGRESS

* Work completed
    - Preflight `PASS WITH ADVISORY`; entering the 10-step `@rel` implementation
* Decisions made
    - Follow the validated plan; no creative docs to apply (creative was skipped)
* Insights
    - None yet; implementation has not started

## 2026-08-29 - BUILD - COMPLETE

* Work completed
    - Implemented all 10 plan steps: stdlib generator + `@rel` parser, migration comments on 0001/0007, committed ERD SSOT, Advanced symlink + nav, Make/CI lockstep and ruff coverage of `scripts/`, sr-query + human docs routing, contributor regen loop, memory-bank pointers
    - 18 new tests in `tests/test_warehouse_schema_docs.py`; engine pytest 853 passed, 5 skipped (4 pre-existing env failures unrelated to this task)
    - `make lint`, `make format-check`, `make schema-docs-check`, `make reuse`, `make docs-build` passed
* Decisions made
    - Followed the validated `@rel` plan; no creative docs to apply
    - Ruff path from engine cwd is `../../scripts` (not `../scripts`); Makefile and CI use the corrected path
    - `assert_coverage` reports missing `@rel` columns before unaccounted snapshot names
    - Importlib test fixture registers the generator in `sys.modules` so dataclasses load under Python 3.14
* Insights
    - Empty `primary_key` → `%% view:` in the Mermaid body; DuckDB types `FLOAT[384]` / `VARCHAR[]` sanitize to `FLOAT_384` / `VARCHAR_ARRAY`
    - `make ci` still stops at `test-dashboard-js` on this machine (Node 22 pin vs PATH Node v26) after schema-docs-check has already passed

## 2026-08-29 - QA - COMPLETE (FAIL)

* Work completed
    - Reviewed the completed warehouse-schema-docs implementation against the Level 3 plan and project brief
    - Re-ran the schema-docs lockstep and the 18 focused ERD-generator tests; both passed
* Decisions made
    - Return to Build for one semantic acceptance gap
* Insights
    - Mermaid `%%` comments do not render. The generator's `%% view: session_token_usage` marker therefore does not distinguish the view from a table for readers of the visual schema.

## 2026-08-29 - BUILD - IN-PROGRESS (QA rework)

* Work completed
    - QA FAIL (fixable): empty-PK view marker is a non-rendered Mermaid comment
* Decisions made
    - Use Mermaid entity-name aliases (`name["name (view)"]`) so the view label is the box title; keep relationship ids as the SQL name
* Insights
    - Official ERD alias syntax (Mermaid 10.5+) renders; `%%` never will

## 2026-08-29 - BUILD - COMPLETE (QA rework)

* Work completed
    - Empty-PK entities now emit `name["name (view)"]` aliases; `%% view:` comments removed
    - View heuristic test requires the alias and rejects comments; toy-render no longer bans all `[` `]` in the mermaid fence
    - Regenerated `skills/sr-query/references/warehouse-schema.md`
    - Schema-docs tests 18 passed; lint/format/schema-docs-check/reuse/docs-build passed; `make test` with Node 22: JS 134 passed, engine 856 passed / 5 skipped / 1 pre-existing identity fail
* Decisions made
    - Mermaid ERD entity aliases are the visible designation; relationship ids stay the SQL name
* Insights
    - A regex that matches `view` anywhere in the mermaid source (including `%%` comments) is not a test of what readers see

## 2026-08-29 - QA - COMPLETE (FAIL, round 2)

* Work completed
    - Re-reviewed after the view-alias rework; prior `%% view:` finding is resolved
    - Subagent was interrupted after writing `.qa-validation-status`; parent transcribed the remaining QA log from that file
* Decisions made
    - Return to Build: restore non-structural column meanings that the ERD cannot carry
* Insights
    - Replacing a SKILL column catalog with a generated ERD removes types/keys/joins from the drift vector, but also drops meanings the picture cannot show (`thinking` not stored, tool outputs not stored, `project_id`/`cwd`/`workspace_key`/`entrypoint` roles) unless those stay in the skill as guardrails
