# Task: warehouse-schema-docs

* Task ID: warehouse-schema-docs
* Complexity: Level 3
* Type: feature

Put a query-facing visual warehouse schema (Mermaid ERD) in the `sr-query` skill and in human docs, generated from the existing head schema golden snapshot (not a dummy DuckDB), with a stdlib generator local developers can run and a CI/`--check` gate that fails on drift. See `memory-bank/active/projectbrief.md` and [issue #127](https://github.com/Texarkanine/stockroom/issues/127).

## Pinned Info

### Derivation pipeline

Why pinned: the whole feature is this pipeline. Dummy-warehouse generation was the issue's first idea; this diagram is the chosen substitute.

```mermaid
flowchart LR
    classDef source fill:#e1f5fe,stroke:#01579b;
    classDef artifact fill:#f3e5f5,stroke:#7b1fa2;
    classDef gate fill:#fff3e0,stroke:#ef6c00;

    Mig["migrations/*.sql"]:::source --> Tests["schema golden tests"]:::gate
    Tests --> Snap["head NNNN_snapshot.json"]:::artifact
    Snap --> Gen["scripts/gen_warehouse_schema.py"]:::source
    Rel["explicit logical relationships"]:::source --> Gen
    Gen --> Skill["skills/sr-query/references/warehouse-schema.md"]:::artifact
    Skill --> Docs["docs/advanced/warehouse-schema.md symlink"]:::artifact
    Gen --> Check["--check / pytest lockstep"]:::gate
```

Logical FKs are **not** in DuckDB (deliberate 0001 invariant). The generator overlays a small explicit relationship list. `session_token_usage` already appears in the head snapshot via `duckdb_columns()`; entities with an empty `primary_key` are drawn as views.

## Component Analysis

### Affected Components
- **Schema goldens** (`skills/sr-search/tests/fixtures/schema/`, `_introspect_schema`): already the migrated product schema (tables + PKs + indexes). **No format change required.** Head today is `0008_snapshot.json` (six names: `sessions`, `messages`, `tool_calls`, `embeddings`, `_sync_state`, `session_token_usage`).
- **ERD generator** (`scripts/gen_warehouse_schema.py`, new): stdlib-only reader of the head snapshot + explicit logical relationships → committed markdown with a Mermaid `erDiagram`. No engine venv, no torch, no on-path `stockroom`, no dummy DB.
- **`sr-query` skill**: `SKILL.md` currently tells agents to introspect `information_schema` and keeps a hand-maintained column catalog "as of migrations 0001–0008". → Point at the generated ERD as the picture; keep join/guardrail doctrine; keep live introspection as a *check*, not the only map.
- **Human docs (Advanced)**: cookbook already uses skill-SSOT + `docs/advanced/cookbook/` symlinks. → Same pattern for the schema page. Architecture `warehouse.md` stays doctrine (no DDL dump); it only routes to the picture.
- **Engine pytest**: new `test_warehouse_schema_docs.py` (generator behavior + lockstep + docs symlink), next to `test_query_cookbook.py`.
- **Make / CI**: new `schema-docs` / `schema-docs-check` targets; engine CI and `make ci` run the check. Docs site CI stays a strict properdocs build (mermaid fence already enabled in `properdocs.yaml`). `lint` / `format` / `format-check` also ruff `../scripts` from the engine cwd so the new stdlib generator is in the same Python lane as the engine (`scripts/localdev.sh` is ignored by ruff).

### Cross-Module Dependencies
- **migrations → goldens**: existing `STOCKROOM_UPDATE_SCHEMA_GOLDEN=1` pytest path. Unchanged; still the schema lock.
- **goldens → generator → skill reference**: one-way derive. Contributors who change schema already update the head snapshot; they then run `make schema-docs`.
- **skill reference → docs symlink**: docs must not fork the body (cookbook contract).
- **generator `--check` → CI**: same function pytest lockstep calls; Make is a thin wrapper so humans and CI share one command.

### Boundary Changes
- **No warehouse DDL / runtime schema change.**
- **New committed skill resource** (PPL-S via existing `skills/**/references/**` REUSE override). Hub layout remains install layout — the file is committed, not generated post-install.
- **New contributor command** `make schema-docs` (write) / `make schema-docs-check` (fail on drift).
- **Public query picture** moves from a stale-prone SKILL prose catalog to a generated ERD. Join rules stay in SKILL.md.

### Invariants & Constraints
- Must preserve committed-layout-equals-install (no generate-on-main for skills).
- Must preserve migrations as DDL source of truth; goldens remain the migrated-schema lock; the ERD is derived.
- Must preserve "no DB-level FOREIGN KEYs" — the diagram shows *logical* relationships, labeled as such.
- Must hold: generator and `--check` run with CPython stdlib only (no plugin install, no engine `.venv` required to regenerate).
- Must preserve Architecture as explanation, not a DDL dump (`docs/architecture/warehouse.md`).
- Non-goal: a `stockroom schema` CLI, live-warehouse dump as the SSOT, or generating files on the `main` branch after merge.

## Open Questions

None - implementation approach is clear. Dummy DuckDB was rejected in favor of the existing head golden snapshot (operator preference + already-CI-gated schema lock). Dual-audience placement follows the cookbook symlink pattern. No creative phase.

## Test Plan (TDD)

### Behaviors to Verify

- **Toy render**: a 2-table snapshot dict (PKs + types including `FLOAT[384]`) → mermaid `erDiagram` containing both entity names, PK markers, and sanitized types (no raw `[` `]` that break Mermaid).
- **Link-free body**: rendered markdown contains no relative markdown links (cookbook recipe-body rule: the same bytes are served from the skill path and the docs symlink). `https://` URLs are allowed; none are required.
- **View heuristic**: an entity with `primary_key: []` is emitted as a view (not a base table), including `session_token_usage` in the toy or a dedicated case.
- **Logical relationships**: configured edges appear as Mermaid relationship lines; tables with no edge still appear as entities.
- **Head snapshot coverage**: rendering the repo's head `NNNN_snapshot.json` includes every key under `tables`.
- **Lockstep**: `check(repo_root)` / CLI `--check` succeeds when the committed SSOT matches a fresh render; fails (nonzero, no write) when the committed file is missing or differs.
- **Write**: CLI default writes `skills/sr-query/references/warehouse-schema.md` so a subsequent `--check` passes.
- **Dual-audience symlink**: `docs/advanced/warehouse-schema.md` is a symlink whose resolve() is the skill SSOT (cookbook contract).

### Edge Cases

- Head snapshot discovery: highest numeric `NNNN_snapshot.json` wins (`0005` has no file; today `0008`).
- DuckDB types `VARCHAR[]`, `FLOAT[384]`, `HUGEINT`, `JSON` are sanitized for Mermaid attributes.
- `--check` does not write the SSOT on failure.
- `_sync_state` is included (it is in the snapshot) even though SKILL calls it uninteresting to query.
- Indexes are **not** required on the ERD (HNSW is snapshot data, not query-forming structure); a one-line generated note is enough.

### Test Infrastructure

- Framework: pytest (`skills/sr-search/pyproject.toml`, xdist `addopts -n auto`)
- Test location: `skills/sr-search/tests/`
- Conventions: `test_*.py`, `repo_root` fixture from `conftest.py`; cookbook dual-audience tests in `test_query_cookbook.py` as the symlink precedent
- New test files: `skills/sr-search/tests/test_warehouse_schema_docs.py`
- Importing the generator: `importlib` from `repo_root / "scripts/gen_warehouse_schema.py"` (script is not an engine package)

### Integration Tests

- Lockstep + symlink tests above are the cross-component integration (goldens ↔ generator ↔ skill file ↔ docs path).
- Do **not** add SKILL.md phrase/link change-detectors. Do **not** assert on `ci.yaml` text, `.pages` nav labels, or Architecture wording.

## Implementation Plan

### 1. ERD generator — executable

- Files: `scripts/gen_warehouse_schema.py`, `skills/sr-search/tests/test_warehouse_schema_docs.py`
- Creative ref: none

1. Stub tests: empty cases in `test_warehouse_schema_docs.py` for toy render, type sanitization, view heuristic, relationship lines, link-free body, head-snapshot coverage, `--check` fail-when-missing (tmp_path), write-then-check (tmp_path).
2. Stub interface: `scripts/gen_warehouse_schema.py` with `load_head_snapshot(fixtures_dir)`, `render_markdown(snapshot)`, `ssot_path(repo_root)`, `check(repo_root)`, `write(repo_root)`, and `main(argv)` — documented signatures, empty/raise bodies.
3. Write tests and run red: assertions on mermaid `erDiagram` text, sanitized `FLOAT[384]`, empty-PK view marking, explicit relationship strings, no relative `](…)` links in the rendered body, every head-snapshot table name present, `check` nonzero on missing/mismatch, `write` then `check` ok. Run `cd skills/sr-search && uv run --no-sync --no-config pytest -n0 tests/test_warehouse_schema_docs.py -v` (expect FAIL).
4. Write code and run green: stdlib JSON + pathlib; discover max `NNNN_snapshot.json`; emit markdown template (title, "logical relationships / no DB FKs", mermaid fence, short index note) **with zero relative markdown links** (human cross-links live on the pages in step 7, not in the generated body); explicit `RELATIONSHIPS` list (`sessions`→`messages`, `messages`→`tool_calls`, `sessions`→`session_token_usage`, polymorphic `embeddings` from `messages` / `tool_calls` via `owner_table`); CLI `python3 scripts/gen_warehouse_schema.py` writes, `--check` compares. Re-run the same pytest until green.

### 2. Commit SSOT + repo lockstep — executable

- Files: `skills/sr-query/references/warehouse-schema.md` (generated), `skills/sr-search/tests/test_warehouse_schema_docs.py` (add lockstep against `repo_root`)
- No tests: n/a — this step is executable

1. Stub tests: add `test_committed_ssot_matches_head_snapshot_render(repo_root)` (empty).
2. Stub interface: none new (`check(repo_root)` already stubbed in step 1).
3. Write tests and run red: assert `check(repo_root)` is success (will fail until the file exists and matches).
4. Write code and run green: run the generator once to write the SSOT; re-run pytest green.

### 3. Dual-audience docs symlink — executable

- Files: `docs/advanced/warehouse-schema.md` (symlink), `docs/advanced/.pages`, `skills/sr-search/tests/test_warehouse_schema_docs.py`
- Creative ref: none (cookbook pattern)

1. Stub tests: `test_docs_warehouse_schema_symlinks_to_skill_ssot(repo_root)` empty.
2. Stub interface: none.
3. Write tests and run red: same assertions as `test_docs_cookbook_pages_symlink_to_ssot_recipes` (is_symlink + resolve to skill SSOT).
4. Write code and run green: create the symlink; add a `Warehouse schema` entry to `docs/advanced/.pages` in the same step (`omitted_files: warn` + no `- ...` wildcard means a page without a nav entry fails `make docs-build`). Do not assert on the nav label (prose). Pytest green.

### 4. Make check wrapper — executable

- Files: `Makefile`, `skills/sr-search/tests/test_warehouse_schema_docs.py`
- Creative ref: none

1. Stub tests: `test_make_schema_docs_check_passes(repo_root)` empty — subprocess `make schema-docs-check` from `repo_root`, assert returncode 0 (precedent: `test_coverage_collection.py` running Make).
2. Stub interface: none (Make target is the interface).
3. Write tests and run red: assertion on returncode 0 (fails until the target exists).
4. Write code and run green: `schema-docs` → `python3 scripts/gen_warehouse_schema.py`; `schema-docs-check` → `python3 scripts/gen_warehouse_schema.py --check`; add `schema-docs-check` to `make ci` and `.PHONY`. Extend `lint` / `format` / `format-check` with a second recipe line `$(UV_RUN) ruff check ../scripts` (and `ruff format` / `ruff format --check` on the same path) so the generator is in the engine ruff lane (`UV_RUN` already cwd's into `skills/sr-search`; `../scripts` is the repo `scripts/` dir; POSIX `localdev.sh` is ignored). Keep the Make pytest as an existence pin only — do not duplicate lockstep assertions there. Pytest green.

### 5. Engine CI step — prose/policy

- Files: `.github/workflows/ci.yaml`
- No tests: prose/policy artifact (workflow YAML). Drift is already gated by pytest in this same job.

1. Add a named step `Warehouse schema docs lockstep` with `working-directory: ${{ github.workspace }}` running `make schema-docs-check` (after engine tests so a missing Make target still fails the job if pytest were skipped in a future CI edit).

### 6. sr-query skill text — prose/policy

- Files: `skills/sr-query/SKILL.md`
- No tests: prose/policy artifact

1. In "What's in the warehouse", lead with a link to [`references/warehouse-schema.md`](references/warehouse-schema.md) as the visual schema.
2. Keep live `information_schema` as a *verify* query, not the primary map.
3. Remove the stale-prone per-column catalog ("as of migrations 0001–0008"); keep identity/join rules, token-grain VIEW guidance, `tool_input` JSON guardrail, `_sync_state` "not interesting" note.

### 7. Human docs routing — prose/policy

- Files: `docs/advanced/index.md`, `docs/advanced/duckdb.md`, `docs/user-guide/search.md`, `docs/architecture/warehouse.md`
- No tests: prose/policy artifact

1. Advanced index + DuckDB + Search: link the picture for query-forming (these pages are single-path, so relative links are fine). Nav already landed in step 3.
2. Architecture warehouse Migrations section: route to Advanced for the ERD; do not paste DDL or the mermaid into Architecture (inclusion bar).

### 8. Contributor regen loop — prose/policy

- Files: `docs/contributing/iteration/engine.md`
- No tests: prose/policy artifact

1. Add a new section (this loop is not documented anywhere in `docs/` today — `STOCKROOM_UPDATE_SCHEMA_GOLDEN` exists only in `tests/test_schema_*.py`). Cover: schema change → update head golden (`STOCKROOM_UPDATE_SCHEMA_GOLDEN=1` on the relevant `test_schema_NNNN.py`) → `make schema-docs` → commit snapshot + generated ERD. If a new table participates in joins, update `RELATIONSHIPS` in the generator. Add the new Make targets to the "Relevant Make Targets" table.
2. Note: regen needs CPython 3 and the repo; it does not need `sr-initialize`, torch, or an on-path shim.

### 9. Standing-contract memory-bank pointers — prose/policy

- Files: `memory-bank/techContext.md` (Warehouse Schema section), `memory-bank/systemPatterns.md` (docs ownership sentence)
- No tests: prose/policy artifact

1. Surgical only if the standing-contract probe fires: techContext points at generated Advanced/skill ERD + `make schema-docs`; systemPatterns docs-ownership mentions schema SSOT beside the cookbook. Skip productContext (no product-audience change).

## Technology Validation

No new technology - validation not required. Stdlib `python3`, existing pytest, existing Mermaid in properdocs, existing cookbook symlink pattern, existing schema goldens.

## Challenges & Mitigations

- **Mermaid vs DuckDB types**: `FLOAT[384]` / `VARCHAR[]` can break attribute syntax. Mitigation: sanitize to mermaid-safe tokens; unit-test those types.
- **No declared FKs**: a dump of `information_schema` would be boxes with no edges. Mitigation: explicit `RELATIONSHIPS` in the generator; document updating it when adding joinable tables.
- **View vs table in snapshot**: `session_token_usage` sits under `tables` with an empty PK. Mitigation: empty PK → view in the diagram; do not churn golden JSON format.
- **Large `sessions` entity (~24 attrs)**: busy but appropriate for docs (illustrate-complexity: completeness beats brevity on the site). Do not split unless preflight/build finds it unreadable.
- **Two-step contributor workflow** (golden then ERD): CI fails if either is skipped; Make target is grep-able; contributing docs name both (new engine.md section — the env var was previously undocumented).
- **Hand-maintained `RELATIONSHIPS`**: a new joinable table still appears as an entity (head-snapshot coverage test) but may lack edges until someone updates the list. Deferred: preflight's `@rel` comment convention in migration SQL plus a coverage assertion. Not in this task (YAGNI vs one six-entity overlay).
- **This checkout has no localdev plugin install**: generator is stdlib and reads fixtures already in the tree; engine pytest still uses `uv run` as today.

## Pre-Mortem

- **Plan assumed we must stand up DuckDB to know the schema**: false — goldens already introspect migrations. Response: pipeline pinned above; dummy DB is a non-goal.
- **SKILL column catalog left in place, ERD added beside it, they drift independently**: plan step 6 deletes the catalog and points at the generated file.
- **Check only in docs CI, so a migration PR that skips docs job description still merges**: put pytest lockstep + `make schema-docs-check` on the engine CI job (always runs on PRs).
- **Generator heuristic mis-labels a future heap table as a view**: product tables have PKs by invariant; contributing note covers it. Already covered by Challenges (view heuristic).
- **`scripts/*.py` silently unlinted**: first Python outside the engine dir. Plan step 4 extends ruff to `../scripts`.
- **Relative links in the generated body work in docs and break in the skill (or vice versa)**: plan step 1 forbids them; a unit test asserts it.
- **Hub≠install because someone generates the ERD in a post-merge main job**: non-goal / invariant; files are committed on the PR.

## Status

- [x] Component analysis complete
- [x] Open questions resolved
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Pre-Mortem complete
- [ ] Preflight
- [ ] Build
- [ ] QA
