# Active Context

## Current Task: warehouse-file-growth, milestone 2 (DuckDB 2.0)
**Phase:** BUILD - COMPLETE

## What Was Done
- Milestone 1 is checked off; milestone 2 is classified Level 3
- Wrote the Level 3 plan in `tasks.md`: 7 steps (scope the Hub filter, finish the shadow script, fresh-clone smoke, two pre-lock gates, the one-commit 2.0 move, live checks, final verification) and 11 behaviours (N1 to N5, S1 to S6)
- Found the nanobind cause by measurement: stockroom's own `_DropUnauthenticatedHubWarning` stays on the `huggingface_hub` logger for the process, which keeps `stockroom.embed` and so `duckdb` alive past nanobind's shutdown check. Removing it after the model loads silences `embed` and `semantic` under 2.0.0
- Measured: full suite green on a 2.0.0 overlay (1,040 passed, 38 skipped); the lock resolves with only duckdb changing; 2.0.0 wheels cover every platform; `warehouse.open()` on 2.0.0 makes a `v2.0.0+` file
- Preflight: PASS WITH ADVISORY (nine advisories, `.preflight-status`)
- Backup made before the build, at the operator's request: `~/.local/share/stockroom/warehouse.issue147-pre-duckdb2.duckdb`, byte copy under the writer flock, SHA-256 equal to the live file (`e7c36f1d…db19c`). Milestone 1 had kept no backup: it deleted its proof copies once the live migrate verified

## Operator decisions (2026-10-22, preflight review)
- Advisory 1 adopted: run overlay commands as `uv --directory skills/sr-search ...` from the repo root
- Advisory 2 adopted: gate 4b through step 6 in one sitting, well before 03:30; if the live file changed since the backup, stop and ask before landing
- Advisory 3 left: the shadow script keeps its "baseline can be deleted" line. Every backup stockroom or a contributor makes is named `warehouse.issue147-<purpose>.duckdb` in the stockroom home, so a later delete-if-present release removes only ours (brief, constraint 11)
- Advisory 4 adopted: `stockroom doctor smoke` joins the live no-`nanobind` checks
- Advisory 5 adopted: gate 4b runs from a fresh clone of the branch on this machine (the Mac recipe). The operator's own Mac runs stay a separate release gate: when the branch is ready, the agent asks him to run them and report back
- Advisory 6 adopted: build-time only; long gates run in the background and their whole logs are read
- Advisory 7 adopted: `techContext` points to `pyproject.toml` for the range
- Advisory 8: the release is a major version; the 2.0 move commit and the pull request title use `feat!:`
- Advisory 9 declined: no worktree as the live engine

## Build (2026-10-22) - COMPLETE
Commits: `fb09cf4` (Hub filter scope), `e011a53` (shadow checks), `57d9a10` (progress save), `ac8c6ca` (`feat!: move the engine to DuckDB 2.0`).

Files modified:
- `skills/sr-search/src/stockroom/embed.py`: `silence_unauthenticated_hub_warning` is a context manager that adds a fresh filter and removes it in `finally`; `BgeEncoder.__init__` wraps only the `SentenceTransformer(...)` construction in it
- `skills/sr-search/tests/test_embed.py`: N1 reworked; N2 (normal/raised), N3, N4 torch-free with fake `torch` / `sentence_transformers` modules; N5 torch-gated subprocess test of `embed` then `semantic`
- `scripts/shadow_duckdb_20.py`: `check_live_copy`, `semantic_answered`, `nanobind_lines`; `_stockroom` returns lines and fails on a `nanobind:` line; one `_WRITER_CHILD` program; `_run_child`, `start`, `storage` removed; docstring with both run forms and the fresh-clone recipe
- `skills/sr-search/tests/test_shadow_duckdb_20.py`: S1 to S6
- `skills/sr-search/pyproject.toml`, `skills/sr-search/uv.lock`, `.github/dependabot.yaml`, `docs/advanced/duckdb.md`, `memory-bank/techContext.md`: the 2.0 move

Integration results:
- N5 on the 2.0.0 overlay with torch: red before the fix (27 leaked instances after `embed`), green after
- Step 3: fresh clone, `--synthetic` recipe passed; live file and checkout `.venv` unchanged
- Gate 4a: 1,053 passed, 36 skipped on the 2.0.0 overlay with torch; all 5 torch-gated tests ran
- Gate 4b: from the clone on a byte copy of the live warehouse, exit 0, `shadow: every phase passed`, no `nanobind` line
- `make ci` green before the commit and again on the landed tree (1,050 passed, 39 skipped); strict docs build green
- Live, supervised: dashboard replaced and serving on 2.0; after-record equals before-record except the engine DuckDB; `ingest`, `embed --verbose` (414 chunks, 0 orphans), `semantic -k 3`, `doctor smoke` exit 0 with no `nanobind` line; rows only grew; DuckDB 1.5.4 still opens the live file read-only (`v1.0.0+`)
- Backup `~/.local/share/stockroom/warehouse.issue147-pre-duckdb2.duckdb` (42,436,407,296 bytes) left in place; the live file matched it until the first live 2.0 write (ingest), which was after every gate passed

Deviations and decisions during build:
- Step 1 stub: the `with` around the model construction went in with the interface stub, because a bare call to a context manager silently adds nothing; the stub body still added the filter for good, so behaviour did not change until the green step
- The lock diff also carries uv 0.12.22's file format (`revision` 3 to 5, scipy's numpy markers dropped). The package set changed only in duckdb (checked by name, version, and source); the root docs lock was already at revision 5 and passes CI's `lock-check`
- `check_live_copy`'s message leaves out the file path, so its version numbers cannot collide with digits in a path
- Finding, not fixed: on DuckDB 2.0.0, a pytest process that loads the engine `conftest` and imports torch in-process prints nanobind leaked-instance lines at exit, exit code unchanged. Plain pytest with DuckDB and stockroom imports, collection without torch, and CI (torch-free) print none; the stockroom command processes print none after step 1. Contributors with torch in `.venv` will see this noise at the end of a local pytest run

## Next Step
- QA (`/niko-qa` in a sub-agent)
- Release gate after QA: the operator runs the shadow script from a fresh clone of the branch on his Macs (the docstring recipe) and reports back. The pull request title must start `feat!:`
