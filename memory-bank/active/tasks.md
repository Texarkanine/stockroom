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
| **C. Python `ensure_engine_env` owned by shim, called from `rectify` (+ optional shim refuse)** | **Accept.** Matches system patterns (shim owns invocation/heal contract; hooks stay thin; doctor stays read-only). Uses torch-safe probe (below). Hooks inherit heal without forking sync logic. |

### Torch-safe sync policy (chosen)

Do **not** use exact `uv sync --frozen` on the heal path (exact `--check` reports “outdated” when torch is present and would uninstall it).

1. Probe: `uv sync --frozen --inexact --check --no-config --directory <app_dir>`
   - exit 0 → locked deps present (torch extras OK) → **noop**
   - exit ≠ 0 → locked deps incomplete → heal
2. Heal: `uv sync --frozen --inexact --no-config --directory <app_dir>`
   - installs missing locked deps **without** removing out-of-lock torch

This is stricter/safer than copying `sr-initialize`’s `[ -d .venv ] \|\| uv sync --frozen` literally, and still satisfies first-time / post-move provisioning. Update `sr-initialize` Step 3 to call the same CLI so policy is not forked.

### Hook timeout

Cold sync can exceed 10s. Existing packaging tests allow Cursor timeout in `1..60`. Raise both harness hooks to **60** seconds. Sync subprocess inside ensure should use a bounded timeout (< hook budget) so a hung uv cannot stall forever; on timeout/failure, rectify still exits 0 (hook must not fail the event) and the shim refuse path (if present) surfaces a clear remedy on `stockroom …`.

## Test Plan (TDD)

### Behaviors to Verify

- **B1 (probe noop):** usable engine env (inexact `--check` would pass) → `ensure_engine_env` reports noop / does not invoke sync install
- **B2 (heal empty):** app_dir with `pyproject.toml`+`uv.lock` but missing or empty `.venv` → ensure runs inexact frozen sync (command shape asserted via stub) and reports synced
- **B3 (torch-safe):** when venv has torch, ensure must **not** run exact sync; heal path uses `--inexact` only
- **B4 (rectify wires ensure):** `rectify` invokes ensure against the target `app_dir` (even on path noop / rectified / absent-dest still? — **ensure runs whenever rectify is asked to heal that app_dir**, including dest-absent noop, so a session can provision env before shim exists… actually dest-absent means user never initialized shim; env heal still useful for plugin-root bootstrap. **Decision: always run ensure for the given `app_dir` at the start of `rectify`.**)
- **B5 (shim refuse):** rendered shim refuses before `uv run --no-sync` when venv python cannot `import duckdb`, with harness remedy text (no silent empty-venv create path for the common failure)
- **B6 (hooks):** Cursor + Claude still rectify-then-dashboard; timeout raised; both still `|| true`; Claude gains `PATH` export parity with Cursor (related reliability while touching hooks)
- **B7 (packaging regression):** existing hook shape assertions updated for timeout/PATH; no dashboard-half `uv run`/`PYTHONPATH`
- **Edge — no pyproject:** ensure noops/refuses safely without calling uv sync
- **Edge — uv missing:** ensure fails soft with reason; rectify still exit 0
- **Regression:** existing shim install/rectify ownership tests still pass

### Test Infrastructure

- Framework: pytest (engine) via root `Makefile` / `skills/sr-search`
- Test location: `skills/sr-search/tests/`
- Conventions: `test_shim.py` (unit policy), `test_shim_cli.py` (CLI), `test_shim_runtime.py` (rendered script via stub uv), `test_packaging.py` (hook JSON shape); fixtures in `conftest.py`
- New test files: prefer extending `test_shim.py` / `test_shim_runtime.py` / `test_packaging.py`; add `test_engine_env.py` only if ensure lives in a dedicated module

## Implementation Plan

1. **Stub ensure API + failing tests (B1–B3, edges)**
   - Files: `skills/sr-search/src/stockroom/engine_env.py` (new), `skills/sr-search/tests/test_engine_env.py` (new)
   - Changes: `EnsureReport` dataclass; `ensure_engine_env(app_dir, *, runner=subprocess.run) -> EnsureReport` with injectable runner for unit tests; document torch-safe inexact policy in module docstring

2. **Implement `ensure_engine_env`**
   - Files: `engine_env.py`
   - Changes: probe with `uv sync --frozen --inexact --check --no-config --directory …`; on failure run heal `uv sync --frozen --inexact --no-config --directory …`; handle missing pyproject / uv errors; bounded timeout

3. **Wire ensure into `rectify` + CLI visibility (B4)**
   - Files: `skills/sr-search/src/stockroom/shim.py`, `tests/test_shim.py`, `tests/test_shim_cli.py`
   - Changes: `rectify` calls `ensure_engine_env(app_dir)` first; extend `ShimReport` or log ensure outcome on stdout when synced; keep rectify exit 0 always; optional `shim ensure-env` action **only if** needed for `sr-initialize` without overloading rectify — prefer dedicated action `ensure-env` for the skill one-liner

4. **Shim template refuse path (B5)**
   - Files: `shim_template.sh`, `tests/test_shim_runtime.py`, `tests/test_shim.py` (render assertions)
   - Changes: before `uv run --no-sync`, require `$APP_DIR/.venv` python can import `duckdb` (sentinel locked dep); else echo remedy and exit 1 — prevents silent empty-venv creation on the on-path path

5. **Hooks timeout + Claude PATH parity (B6–B7)**
   - Files: `hooks/cursor-hooks.json`, `hooks/claude-hooks.json`, `tests/test_packaging.py`
   - Changes: `timeout: 60`; Claude command exports `PATH` like Cursor; update assertions

6. **Docs / skill contract**
   - Files: `skills/sr-initialize/SKILL.md` Step 3, `docs/development.md` and/or `docs/using.md` if they describe heal-only-path, `skills/sr-search/references/system-model.md` if it claims path-only heal
   - Changes: document that session/workspace hooks heal path **and** env via rectify→ensure; replace naive `[ -d .venv ]` sync with `python -m stockroom shim ensure-env` (plugin-root bootstrap) or equivalent; note torch-safe inexact heal

7. **Full verification**
   - Run targeted tests then full `make test` / lint as required by project practices

## Technology Validation

No new technology — validation not required. Uses existing `uv` CLI flags (`--inexact`, `--check`, `--frozen`, `--no-config`) already required by the torch-safe contract.

## Dependencies

- Existing: `uv` on PATH (already a prerequisite)
- Issue [#17](https://github.com/Texarkanine/stockroom/issues/17) acceptance criteria
- Must not break torch-safe contract in `docs/development.md` / `sr-initialize`

## Challenges & Mitigations

- **Empty `.venv` from hook’s own `uv run --no-sync` before ensure runs:** Mitigated by inexact `--check` (detects incomplete env) rather than `[ -d .venv ]`.
- **Exact sync would uninstall torch:** Heal path never exact-syncs; only `--inexact`.
- **Hook 10s timeout kills cold sync:** Raise to 60s; bound ensure subprocess timeout; soft-fail keeps hook green; shim refuse gives clear remedy until a later successful heal.
- **`doctor smoke` needs torch:** Acceptance “doctor smoke or dashboard” — dashboard/duckdb is the right post-move bar; torch remains out-of-band (`sr-initialize` / `make torch`). Do not claim smoke passes without torch re-provision on a brand-new engine dir.
- **Shim duckdb sentinel vs full lock check:** Sentinel is cheap POSIX-side refuse; full correctness remains ensure’s `uv sync --check`. Accept sentinel as defense-in-depth, not the heal authority.

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [ ] Preflight
- [ ] Build
- [ ] QA
