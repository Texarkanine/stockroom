# Progress

Heal engine-env staleness after plugin-root moves so one session/workspace-open cycle leaves `stockroom` runnable without a manual full re-init. Verify [#17](https://github.com/Texarkanine/stockroom/issues/17) claims, evaluate approaches, implement the best fix within stockroom constraints.

**Complexity:** Level 2

## 2026-07-10 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - Clarified intent with operator: verify issue claims; evaluate proposed solutions; implement best solution for stockroom
    - Verified issue diagnosis against codebase (hooks path-only; shim `--no-sync`; guarded sync only in `sr-initialize` prose; no env-heal owner)
    - Classified as Level 2
* Decisions made
    - Level 2 (multi-component bug + approach selection in plan; not L3 architecture/feature)
    - Do not default to issue #17’s preferred option (1) without plan-phase evaluation
* Insights
    - Hook 10s timeout may make “sync inside hook” impractical on cold cache
    - Empty-but-present `.venv` breaks naive `[ -d .venv ]` guards
    - Torch must be re-provisioned separately after a fresh engine dir; dep sync alone does not restore embed/semantic

## 2026-07-10 - PLAN - COMPLETE

* Work completed
    - Reproduced empty-venv footgun; confirmed `uv sync --frozen --inexact --check` is torch-safe readiness probe (exact `--check` wants to uninstall torch)
    - Selected design C: `ensure_engine_env` in Python, called from `rectify`; shim duckdb sentinel refuse; hook timeout 60s + Claude PATH parity; update `sr-initialize` to same CLI
    - Authored full L2 test/implementation plan in `tasks.md`
* Decisions made
    - Heal path never exact-syncs — only `--inexact` (safer than copying issue/sr-initialize `[ -d .venv ] || uv sync --frozen` literally)
    - Reject hook-JSON shell sync duplication and refusal-only approaches as primary fix
    - Post-move success bar is runnable locked deps / dashboard — not `doctor smoke` without torch re-provision
* Insights
    - Hook bootstrap `uv run --no-sync` creates the empty `.venv` *before* Python starts; ensure must detect incompleteness, not directory presence

## 2026-07-10 - PREFLIGHT - COMPLETE

* Work completed
    - Validated plan vs conventions, deps, conflicts, completeness
    - Amended plan: per-step TDD; `python3` rectify bootstrap; `system-model.md` fix
    - Wrote `.preflight-status` = PASS
* Decisions made
    - Heal authority stays in Python ensure; hooks must not use `uv run --no-sync` for rectify bootstrap
* Insights
    - `shim` + `engine_env` are stdlib-only, so plugin-root `PYTHONPATH` + `python3 -m stockroom` is a valid chicken-egg bootstrap without touching the project venv

## 2026-07-10 - BUILD - COMPLETE

* Work completed
    - `ensure_engine_env` + tests; CLI `ensure-env`; rectify wiring; shim duckdb refuse; hook bootstrap/timeout/PATH; docs
    - Full suite: 435 passed, 3 skipped; ruff clean
    - Manual repro: empty `.venv` from `--no-sync` → `ensure-env` → `import duckdb` ok
* Decisions made
    - Heal path always `--inexact` (never exact)
    - Hook rectify via `python3` not `uv run --no-sync`
* Insights
    - Cold sync of locked deps was ~2s with warm cache in repro; 60s hook budget is adequate for typical updates

## 2026-07-10 - QA - COMPLETE

* Work completed
    - Semantic review PASS; trivial doc/stderr/systemPatterns/using.md fixes
    - Wrote `.qa-validation-status` = PASS
* Decisions made
    - No substantive redesign; heal design held under review
* Insights
    - Ignoring ensure failures inside rectify would hide manual-debug signal; stderr print is cheap and hook-silenced

## 2026-07-10 - REFLECT - COMPLETE

* Work completed
    - Wrote `reflection/reflection-fix-plugin-env-heal-after-move.md`
    - Reconciled persistent files (systemPatterns already current)
* Decisions made
    - Standalone task → next operator step is `/niko-archive`
* Insights
    - Inexact `--check` is the torch-safe readiness probe; exact `--check` is a footgun after torch

## 2026-07-10 - REWORK INITIATED

* Operator feedback: durable torch-index record is **in scope for #17**. After plugin update, rectify recreates venv without torch → overnight embed fails silently → semantic breaks. Manual torch reinstall every plugin update is a nonstarter.
* Cleared tasks/activeContext/preflight/qa status; preserving projectbrief, progress, reflection.

## 2026-07-10 - REWORK BUILD - COMPLETE

* Work completed
    - `torch_source` + `torch_cli`; ensure_engine_env heals torch from durable index
    - `sr-initialize` / `make torch` / docs / hook timeout 300
    - 445 passed, 3 skipped; ruff clean
* Decisions made
    - Record at `{stockroom_home}/torch-index` (one https URL line)
    - Never guess an index when missing
* Insights
    - Existing installs need a one-time `stockroom torch record --index …` (or re-run `make torch`) before heal can restore torch

## 2026-07-10 - REWORK QA + REFLECT - COMPLETE

* Work completed
    - QA PASS on torch persistence rework; reflection updated
* Decisions made
    - Ready for `/niko-archive`

## 2026-07-10 - PLAN - COMPLETE (hashed torch freeze rework)

* Work completed
    - Operator confirmed freeze-after-smoke contract; planned replacement of floating index heal
    - Tech validation: `uv pip compile --generate-hashes` works for pinned `torch==2.7.1+cpu`
    - Wrote implementation/test plan in `tasks.md`; extended `projectbrief` rework section
* Decisions made
    - Artifact: `{stockroom_home}/torch-requirements.txt` + sidecar `torch-index`
    - No floating heal fallback for legacy index-only
    - `docs/torch.md` for manual path; freeze replaces CLI `record`
* Insights
    - Freeze will also pin some PyPI transitives of torch; install after inexact sync, document drift

## 2026-07-10 - PREFLIGHT - COMPLETE (hashed torch freeze)

* Work completed
    - Validated plan vs TDD encoding, conventions, completeness
    - Amendments: default `--app-dir`; `--emit-index-url` for heal resolve; cleared stale QA status
    - `.preflight-status` = PASS
* Decisions made
    - Ready for build
