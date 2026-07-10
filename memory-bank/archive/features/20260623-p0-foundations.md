---
task_id: p0-foundations
complexity_level: 3
date: 2026-06-23
status: completed
---

# TASK ARCHIVE: Phase 0 — Foundations

## SUMMARY

Stood up the trustworthy, reproducible, test-first substrate for stockroom: a dual-manifest plugin scaffold (Cursor + Claude Code) over a shared `skills/` tree with no build step, a hermetically locked uv project inside `skills/sr-search/` that holds torch out of the lock, release-please versioning synced into both manifests, enforced layered REUSE/SPDX licensing, and a pytest/ruff/reuse harness with CI. Zero product behavior shipped — search lands in Phase 2. Final gate: 17 tests green; `ruff check`, `ruff format --check`, `uv lock --locked --no-config`, and whole-tree `reuse lint` all clean. Post-reflect, a root `Makefile` became the dev entrypoint (`make help`, `make sync`, `make lock`, `make test`, `make ci`).

## REQUIREMENTS

From the project brief:

- **Dual-manifest plugin scaffold** — `.cursor-plugin/plugin.json` and `.claude-plugin/plugin.json` over a shared `skills/` tree; AGPLv3 confirmed; committed layout = install layout; both harnesses from day one.
- **release-please wired** — config + manifest sync one version into both plugin manifests in lockstep.
- **Locked uv project skeleton** inside the engine-bearing skill — `pyproject.toml` with `requires-python`, torch-exclusion override, and hermetic `uv.lock` via `uv lock --no-config`; torch-safe run contract documented.
- **Test, lint, and format harness** — pytest + ruff + reuse; one trivial green test minimum.
- **No product code** — substrate only.

Constraints: uv-locked except torch; AGPLv3; both manifests from start; no build step; clean-room w.r.t. `claude-warehouse`.

Acceptance criteria (as delivered):

1. Fresh clone resolves locked env hermetically — PyPI-only, hashed, no torch/CUDA/nvidia, no ambient-config leakage ✓
2. Test suite green; formatter and linter clean ✓
3. Both plugin manifests validate ✓
4. release-please config-valid + workflow-present + lockstep-tested (live release flip deferred to operator post-merge; end-to-end proof Phase 5) ✓
5. No product behavior ✓

## IMPLEMENTATION

### Repository layout (end of Phase 0)

```
stockroom/
├── .cursor-plugin/plugin.json
├── .claude-plugin/plugin.json
├── .github/workflows/{ci.yml, release-please.yaml}
├── .gitignore
├── LICENSE + LICENSES/*.txt + REUSE.toml
├── Makefile                          ← post-reflect dev entrypoint
├── README.md
├── release-please-config.json
├── .release-please-manifest.json
└── skills/
    └── sr-search/                      ← engine-bearing skill (skeleton SKILL.md)
        ├── SKILL.md
        ├── pyproject.toml
        ├── uv.lock
        ├── src/stockroom/__init__.py
        └── tests/
```

### Key design decisions

**Engine home = `skills/sr-search/`** (operator confirmed via `/niko-build`). The core entrypoint skill hosts the shared Python engine (`pyproject.toml`, `uv.lock`, `src/stockroom/`, `tests/`). Alternative `sr-initialize` was flagged but not chosen. Resolution is plugin-root-relative, so the host dir is invisible to consumers.

**Skeleton-skill convention:** `SKILL.md` ships with real front-matter and an honest body stating the dir is the engine home and search behavior lands in Phase 2 — not a dummy.

**uv shape:** `[tool.uv] package = false` (run-in-place; deps locked, stockroom never built/installed), `src/` layout, `pythonpath = ["src"]` for tests.

**Torch exception:** `override-dependencies = ["torch; python_full_version < '3'"]` — impossible marker keeps torch and CUDA/nvidia transitives out of the lock. Lock generated with `uv lock --no-config`. Runtime deps locked now: `duckdb`, `sentence-transformers`, `numpy` (proves override works). Lock = 51 packages (o9 spike's 38 + dev group). uv provisioned Python 3.13.7.

**Cross-skill resolution (for later phases):** PLUGIN_ROOT check-once-on-startup + `find -L` dev fallback; torch-safe `uv run --project "$APP_DIR" --no-sync`. Documented in `systemPatterns.md`.

**Layered REUSE licensing:** AGPL base on all code; PPL-S layered on `skills/**` prompt content; AGPL re-asserted on code-shaped paths within `skills/**`; NOASSERTION on `.cursor/**`. Enforced by `reuse lint` + spot-check tests via `reuse spdx`.

**release-please:** Adapted from `slobac` — `release-type: simple`, `extra-files` writes `$.version` into both `plugin.json` paths. GitHub App token pattern in workflow; operator flips live releases post-merge.

### Six-step TDD build (executed in order)

1. Bootstrap uv engine + pytest harness (`test_smoke.py` red → pyproject + package green)
2. Hermetic torch-free lock (`test_lock_hermetic.py` red → `uv lock --no-config` green; red staged by moving lock aside)
3. Skeleton skill + dual manifests (`test_packaging.py` portions)
4. release-please wiring (`test_packaging.py` lockstep + extra-files)
5. Layered REUSE (`test_licensing.py` → `reuse lint` green)
6. CI + README + format; lock-staleness guard (`test_lock_is_not_stale`)

### In-scope deviations

- Root `.gitignore` created in step 1 (not step 6) — needed to commit without `.venv/`/`__pycache__/`.
- `triton` added to lock test forbidden-exact set (torch companion; defensive).

### Post-reflect additions (operator iteration)

- Root **`Makefile`** — dev entrypoint wrapping `skills/sr-search/` cd'ing and `--no-config` / `--no-sync` flags. Targets: `sync`, `lock`, `lock-check`, `test`, `lint`, `format`, `format-check`, `reuse`, `ci`.
- **`README.md`**, **`memory-bank/techContext.md`**, **`memory-bank/systemPatterns.md`** updated to point at Makefile as the canonical local iteration path.

### Key files

| Area | Files |
|------|-------|
| Engine | `skills/sr-search/pyproject.toml`, `uv.lock`, `src/stockroom/__init__.py` |
| Tests | `tests/{conftest.py,test_smoke,test_lock_hermetic,test_packaging,test_licensing}.py` |
| Plugin | `.cursor-plugin/plugin.json`, `.claude-plugin/plugin.json`, `skills/sr-search/SKILL.md` |
| Release | `release-please-config.json`, `.release-please-manifest.json`, `.github/workflows/release-please.yaml` |
| Licensing | `REUSE.toml`, `LICENSES/*.txt` |
| Harness | `.github/workflows/ci.yml`, `.gitignore`, `Makefile`, `README.md` |

## TESTING

17 pytest tests in `skills/sr-search/tests/`:

- `test_smoke.py` — harness sanity + `import stockroom` + `__version__`
- `test_lock_hermetic.py` — torch/CUDA/nvidia-free lock; PyPI+hashed packages; manifest override; pyproject contract; `uv lock --locked` staleness
- `test_packaging.py` — manifest validity, version lockstep, skills pointer, skeleton front-matter, release-please extra-files
- `test_licensing.py` — whole-tree `reuse lint`; AGPL on `.py` in skills; PPL-S on `SKILL.md`

Integration gate (local + CI-aligned):

```
make ci   # or individually: sync, lock-check, lint, format-check, test, reuse
```

QA semantic review: PASS (one doc-completeness fix to `techContext.md` during QA).

## LESSONS LEARNED

### Technical

- **Locked-project TDD bootstrap paradox:** When the lockfile is an artifact-under-test, you cannot have "no lock" and a runnable test interpreter simultaneously. Stage the red by moving an existing lock aside; write lock assertions to parse files, not import the env.
- **`uv lock --no-config` is load-bearing** for hermeticity — ambient `~/.config/uv/uv.toml` can leak pytorch indexes into the lock. Standing CI guard (`uv lock --locked --no-config`) catches drift.
- **REUSE last-match-wins ordering** cleanly expresses "AGPL code inside a PPL-S skill dir" — base AGPL → `skills/**` PPL-S → code-shaped `skills/**` globs back to AGPL.
- **`reuse spdx` (tag-value output)** is reliable for per-file license resolution tests, not just whole-tree `reuse lint`.

### Process

- **Preflight earned its keep** — promoted REUSE from advisory to enforced; added lock-staleness guard before build started.
- **Planning thoroughness → build calm** — pinning repo layout and PLUGIN_ROOT pattern in `systemPatterns.md` meant build was pure execution against `slobac` + o9-spike references.
- **Skip creative was correct** — all open questions resolved at high confidence during planning; nothing during build needed re-exploration.
- **"Reconcile docs that point at new artifacts" belongs in the final build step**, not QA — the sole QA finding was `techContext.md` pointer debt the plan never scheduled.

## PROCESS IMPROVEMENTS

- Add an explicit final build step: "update persistent memory-bank pointers to newly-created canonical artifacts" (Makefile, pyproject, workflows, etc.).
- For substrate/config phases, treat TDD cycle boundaries as aspirational — bootstrap order (`.gitignore` first, lock-before-interpreter) legitimately overrides tidy one-test-one-artifact framing.
- When adding a dev entrypoint (Makefile), update README + `techContext.md` in the same changeset — don't leave raw `uv` commands as the primary path in user-facing docs.

## TECHNICAL IMPROVEMENTS

- Operator post-merge: wire GitHub App token (`HELPER_APP_ID` / `HELPER_APP_PRIVATE_KEY`) for release-please so release PRs trigger CI.
- Phase 5 owns end-to-end live release proof; Phase 0 proved config + lockstep only.
- Future `sr-*` skills should implement PLUGIN_ROOT resolution per `systemPatterns.md` when they consume the engine.

## NEXT STEPS

- **Phase 1** (per `planning/roadmap.md`): schema + migrations — first product substrate.
- Operator: flip release-please on GitHub after merge if desired.
- Run `/niko` to begin the next roadmap phase task.

## CREATIVE PHASE DECISIONS

No creative phase was executed. All design decisions were resolved during planning at high confidence:

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Engine host | `skills/sr-search/` | Core entrypoint coherence; plugin-root-relative resolution makes host invisible to consumers |
| Skill presence | Skeleton `SKILL.md` | Honest placeholder from Phase 0; operator confirmed skeleton skills acceptable |
| uv shape | `package = false` + `src/` | No build backend; honors no-build-step |
| Licensing | Layered REUSE (AGPL + PPL-S) | Operator intentional; mirrors `slobac` |
| Live release | Config-valid now; live flip post-merge | Not fully exercisable until GitHub App token provisioned |
