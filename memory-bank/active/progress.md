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
