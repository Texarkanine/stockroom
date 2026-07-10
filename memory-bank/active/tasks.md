# Task: fix-plugin-env-heal-after-move

* Task ID: fix-plugin-env-heal-after-move
* Complexity: Level 2
* Type: bug fix

After a plugin-root move (marketplace hash change, reinstall, or rsync without `.venv`), path-only `shim rectify` leaves the on-path shim pointed at an engine dir with no usable uv env. Heal **environment** readiness in the same tested owner as path healing (`stockroom.shim` / `rectify`), using a torch-safe readiness probe — not a naive `[ -d .venv ]` guard and not duplicated shell in both hook JSON files.

## Verified root cause (issue #17 claims)

| Claim | Verdict |
| --- | --- |
| Hooks only rectify path, never re-sync | **True** — `hooks/cursor-hooks.json`, `hooks/claude-hooks.json` |
| Shim uses `uv run --no-sync` | **True** — `shim_template.sh` |
| Rectify can succeed without duckdb | **True** — stdlib-only + `PYTHONPATH` bootstrap |
| `sr-initialize` guarded sync is the only env owner | **True** — skill prose only; no Python helper |
| Missing `.venv` + `--no-sync` creates empty venv then import-fails | **True** — reproduced under `/tmp` |

## Approach evaluation (best for stockroom)

| Option | Verdict |
| --- | --- |
| **A. Shell `uv sync` in both hook JSON files** (issue preference #1, literal) | **Reject as primary.** Duplicates untested policy in two schemas; naive `[ -d .venv ]` is wrong after `uv run --no-sync` creates an empty dir; violates “one tested owner” for rendered artifacts. |
| **B. Shim-runtime refusal only** (issue preference #2 alone) | **Reject as primary.** Improves errors but does **not** make “new session heals” true. |
| **C. Python `ensure_engine_env` owned by shim, called from `rectify` (+ shim refuse + stdlib hook bootstrap)** | **Accept.** Matches system patterns (shim owns invocation/heal contract; hooks stay thin; doctor stays read-only). |

### Torch-safe sync policy (chosen)

Do **not** use exact `uv sync --frozen` on the heal path (exact `--check` reports “outdated” when torch is present and would uninstall it).

1. Probe: `uv sync --frozen --inexact --check --no-config --directory <app_dir>`
   - exit 0 → locked deps present (torch extras OK) → **noop**
   - exit ≠ 0 → locked deps incomplete → heal
2. Heal: `uv sync --frozen --inexact --no-config --directory <app_dir>`
   - installs missing locked deps **without** removing out-of-lock torch

Update `sr-initialize` Step 3 to call `shim ensure-env` so policy is not forked.

### Hook bootstrap (preflight amendment)

Rectify + ensure are **stdlib-only**. Change hook rectify bootstrap from `uv run --project … --no-sync` to:

`PYTHONPATH="${*_PLUGIN_ROOT}/skills/sr-search/src" python3 -m stockroom shim rectify …`

so the hook never creates an empty project `.venv` before ensure runs. `uv` is invoked only inside `ensure_engine_env`.

### Hook timeout

Raise both harness hooks to **60** seconds. Ensure subprocess timeout bounded below that; on failure rectify still exits 0; shim refuse surfaces remedy.

## Test Plan (TDD)

### Behaviors to Verify

- **B1 (probe noop):** usable engine env → `ensure_engine_env` reports noop / does not invoke heal sync
- **B2 (heal empty):** app_dir with `pyproject.toml`+`uv.lock` but missing/empty `.venv` → ensure runs inexact frozen sync (stubbed runner) and reports synced
- **B3 (torch-safe):** heal command always includes `--inexact`; never exact-only sync
- **B4 (rectify wires ensure):** `rectify` always calls ensure for `app_dir` first (including dest-absent noop)
- **B5 (ensure-env CLI):** `python -m stockroom shim ensure-env --app-dir …` exercises ensure and exits 0 on success / soft-fail policy as designed
- **B6 (shim refuse):** rendered shim refuses before `uv run --no-sync` when venv python cannot `import duckdb`
- **B7 (hooks):** Cursor + Claude: stdlib `python3` rectify bootstrap (no `uv run` in rectify half), rectify-then-dashboard, timeout 60, `|| true`; Claude PATH export parity
- **Edge — no pyproject:** ensure noops/refuses safely without calling uv sync
- **Edge — uv missing / timeout:** ensure fails soft with reason; rectify still exit 0
- **Regression:** existing shim ownership / packaging tests updated and green

### Test Infrastructure

- Framework: pytest via `skills/sr-search`
- Test location: `skills/sr-search/tests/`
- Conventions: `test_shim.py`, `test_shim_cli.py`, `test_shim_runtime.py`, `test_packaging.py`
- New test files: `test_engine_env.py`

## Implementation Plan

Each numbered step is one TDD cycle: **write/adjust failing tests → implement → re-run those tests green** before the next step.

1. **`ensure_engine_env` (B1–B3, edges)**
   - Tests first: `skills/sr-search/tests/test_engine_env.py` (stub `runner`)
   - Then implement: `skills/sr-search/src/stockroom/engine_env.py` — `EnsureReport`, `ensure_engine_env(app_dir, *, runner=…)`, inexact check/heal, timeouts, missing pyproject/uv handling

2. **`shim ensure-env` CLI (B5)**
   - Tests first: extend `tests/test_shim_cli.py` (+ help text expectations in `test_shim.py` / dispatcher if needed)
   - Then implement: `shim.py` — add `ensure-env` action calling `ensure_engine_env`; update parser/help

3. **Wire ensure into `rectify` (B4)**
   - Tests first: extend `tests/test_shim.py` / `test_shim_cli.py` so rectify invokes ensure (mock/spy)
   - Then implement: `rectify()` calls `ensure_engine_env(app_dir)` before path logic; keep exit 0

4. **Shim template refuse (B6)**
   - Tests first: extend `tests/test_shim_runtime.py` + render assertions in `test_shim.py`
   - Then implement: `shim_template.sh` — duckdb import check before `uv run --no-sync`

5. **Hooks bootstrap + timeout + Claude PATH (B7)**
   - Tests first: update `tests/test_packaging.py` expectations (python3 bootstrap, no uv run in rectify half, timeout 60, Claude PATH)
   - Then implement: `hooks/cursor-hooks.json`, `hooks/claude-hooks.json`

6. **Docs / skill contract**
   - Files: `skills/sr-initialize/SKILL.md` Step 3 → `shim ensure-env`; `skills/sr-search/references/system-model.md` (fix false “shim re-resolves” claim; document hook rectify path+env heal); touch `docs/development.md` / `docs/using.md` only if they describe heal/sync incorrectly
   - No production code in this step

7. **Full verification**
   - Targeted tests for this change, then full suite per project practices (`make test` / lint as applicable)

## Technology Validation

No new technology — validation not required.

## Dependencies

- Existing `uv` on PATH
- Issue [#17](https://github.com/Texarkanine/stockroom/issues/17)
- Torch-safe contract in `docs/development.md` / `sr-initialize`

## Challenges & Mitigations

- **Empty `.venv` from `uv run --no-sync`:** Eliminated for hooks via stdlib `python3` bootstrap; ensure still detects incomplete envs via inexact `--check`.
- **Exact sync would uninstall torch:** Heal path never exact-syncs.
- **Hook timeout:** 60s + bounded ensure timeout + soft-fail + shim refuse.
- **`doctor smoke` needs torch:** Post-move bar is locked deps / dashboard; torch stays out-of-band.
- **`python3` missing/too old in hook env:** Unlikely; ensure/rectify still soft-fail with `|| true`. If needed later, fall back documented in reflection — not blocking.

## Preflight Amendments

- Strengthened per-step TDD ordering (blocking fix).
- Hook rectify bootstrap → `python3 -m stockroom` (stdlib) instead of `uv run --no-sync`.
- Explicitly include `system-model.md` correction in docs step.

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Preflight
- [x] Build
- [x] QA
