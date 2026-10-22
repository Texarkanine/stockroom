# Active Context

## Current Task: warehouse-file-growth, milestone 2 (DuckDB 2.0)
**Phase:** BUILD - IN PROGRESS

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

## Next Step
- Build step 1: scope the Hub-notice filter to the model load
