---
task_id: fix-session-start-heal-after-plugin-move
complexity_level: 2
date: 2026-07-10
status: completed
---

# TASK ARCHIVE: fix-session-start-heal-after-plugin-move

## SUMMARY

Closed the session-start heal chicken-and-egg from [issue #25](https://github.com/Texarkanine/stockroom/issues/25): after a marketplace plugin-hash move, `shim rectify` died on `import duckdb` before `ensure_engine_env` could sync. Extracted stdlib-only home resolution into `stockroom.home` so the heal stack (`shim` → `engine_env` → `torch_source`) runs on a bare `uv python find` interpreter. Hooks stayed thin; warehouse re-exports preserve existing callers.

## REQUIREMENTS

1. Heal entrypoint must not import DuckDB (or other project site-packages) before `ensure_engine_env` can sync.
2. Prefer dep-light / stdlib-only heal import graph over shell-sync-first duplication in hooks.
3. Preserve torch restore from hashed freeze; soft-fail when freeze missing.
4. Keep thin hooks; Python remains the single heal-policy owner.
5. Do not regress to premature `uv run --no-sync` (empty-`.venv` footgun).
6. Pin with tests that `import stockroom.shim` and `python -m stockroom shim --help` do not load duckdb.

## IMPLEMENTATION

### Approach

Moved `HOME_ENV_VAR` / XDG resolution / `resolve_home` / `home_dir` into `stockroom.home` (stdlib only). Pointed `torch_source` at that module; `warehouse` re-exports the same names. Hooks unchanged.

### Key files

| Area | Files |
| --- | --- |
| New home module | `skills/sr-search/src/stockroom/home.py` |
| Heal stack | `skills/sr-search/src/stockroom/torch_source.py` → `stockroom.home` |
| Re-exports | `skills/sr-search/src/stockroom/warehouse.py` |
| Import-graph pins | `skills/sr-search/tests/test_shim_import_graph.py` |
| Patterns | `memory-bank/systemPatterns.md` (stdlib-only heal import note) |

## TESTING

- TDD: subprocess import-graph tests (bare `import stockroom.shim` and dispatcher `shim --help`) assert duckdb absent from `sys.modules`; existing home/torch/engine_env/packaging suites kept green.
- Full suite: **470 passed, 3 skipped**; ruff check/format clean.
- `/niko-qa` semantic review PASS; no fixes required.
- Live “delete `.venv` + dead hash” acceptance remains an optional operator smoke on a real plugin cache — unit pins cover reachability; ensure/torch tests cover heal once imported.

## LESSONS LEARNED

### Technical

Heal-path import weight is a first-class contract: anything on the `shim` → `engine_env` → `torch_source` chain must stay free of warehouse/DuckDB (and similarly heavy) imports, or the next bootstrap tweak will re-break auto-heal.

### Process

Nothing notable. Plan sequence matched the build; the only preflight amendment (also pin dispatcher `shim --help`) was useful and cheap.

### Million-dollar question

Home resolution would have lived in a stdlib-only module from the start, with warehouse importing it — not the other way around. That is essentially what we built.

## PROCESS IMPROVEMENTS

None — plan, preflight, build, QA, and reflect held without rework.

## TECHNICAL IMPROVEMENTS

None beyond the shipped extract. Keep heal-path imports stdlib-only as a durable packaging contract.

## NEXT STEPS

None. Task complete and archived. Optional: operator smoke of delete-`.venv` + dead-hash on a live plugin cache if desired for issue #25 acceptance confidence.
