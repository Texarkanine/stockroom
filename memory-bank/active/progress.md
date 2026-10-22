# Progress

L4 milestone 2 of 7 for `warehouse-file-growth` ([issue 147](https://github.com/Texarkanine/stockroom/issues/147), as amended in `memory-bank/active/projectbrief.md`): move the engine to DuckDB 2.0 and prove it on a copy of a real warehouse. The engine lock pins DuckDB 2.0 and the dependency range is `>=2.0,<2.1`; Dependabot ignores duckdb `>= 2.1.0` in the engine block. `scripts/shadow_duckdb_20.py` runs from a branch clone under a DuckDB 2.0 overlay against a copy of a real warehouse: it copies under the writer flock, checks equality after a 2.0 checkpoint, runs ingest and embed under 2.0, then has DuckDB 1.5.4 write to the copy, and 2.0 opens it after that. It exits 0 on this machine's warehouse before the 2.0 lock lands here. `docs/advanced/duckdb.md` states the 2.0 format and who can open it. `stockroom embed` and `stockroom semantic` print no nanobind leaked-instance warnings at exit under 2.0, unless the operator accepts them once the cause is known. The 2.0 lock is the last change this milestone brings into this checkout.

**Complexity:** Level 3

## 2026-10-22 - COMPLEXITY ANALYSIS - COMPLETE

* Work completed
    - Checked off milestone 1 in `milestones.md` and cleared its sub-run files (its reflection stays in `reflection/`)
    - Classified milestone 2, "Move the engine to DuckDB 2.0 and prove it on a copy of a real warehouse"
* Decisions made
    - Level 3, as the L4 re-plan estimated. The lock and dependency range, Dependabot, the rest of the shadow script and its tests, a live-copy run before the lock lands, a user-facing doc page, and the nanobind warnings (cause unknown) all change or need investigation. The commit hook syncs this checkout's environment to the working-tree lock, so the lock change is live on this machine at once

## 2026-10-22 - PLAN - COMPLETE

* Work completed
    - Wrote the Level 3 plan in `tasks.md`: 7 steps and 11 behaviours (N1 to N5 for the Hub filter and the exit warning, S1 to S6 for the shadow script)
    - Probed the nanobind warnings on a DuckDB 2.0.0 overlay with torch installed from the hashed freeze (`scratchpad/m2/nanobind_probe*.py`)
    - Ran the full engine suite on a 2.0.0 overlay (1,040 passed, 38 skipped), resolved the 2.0 lock in a scratch copy, and checked the 2.0.0 wheels and the new-file tag
* Decisions made
    - Fix the nanobind warnings at their cause rather than ask the operator to accept them: `silence_unauthenticated_hub_warning` becomes a context manager around the model load
    - Pin 2.0.0, the only final 2.0 release; Dependabot ignores `>=2.1.0`
    - The 2.0 move is one commit (range, lock, Dependabot, doc page, techContext) after two gates: the full suite on a 2.0 overlay with torch, and the shadow run on a copy of the live warehouse. The shadow baseline stays as the rollback copy, and the first live 2.0 writes are supervised in the build, not left to 03:30
    - No pin test (change-detector). The shadow script fails on any nanobind line, so the operator's Mac runs check the fix there too
* Insights
    - The warning is not a DuckDB refcount bug in stockroom's queries: DuckDB with any binding, torch, and a plain sentence-transformers load are all clean. It is stockroom's own logger filter, which outlives the model load
    - A torch-free process cannot reproduce it, so only a torch-gated test can check the exit warning itself; a torch-free test checks the filter's scope

## 2026-10-22 - PREFLIGHT - COMPLETE

* Work completed
    - Checked the Level 3 plan against the code: `embed.py`, `test_embed.py`, `scripts/shadow_duckdb_20.py` and its tests, `semantic.py` / `render.py` TSV output, `doctor.py`, `.github/dependabot.yaml`, `docs/advanced/duckdb.md`, the Makefile, and the commit hook
    - Confirmed on DuckDB 1.5.4 that S1 and S4 hold as written: a migrated `v1.0.0` file reads `v1.0.0+`, schema 9, no non-primary index; a `v1.2.0` file reads `v1.2.0+`
    - Result: `.preflight-status` first line `PASS WITH ADVISORY`. No TDD step swap and no strike
* Decisions made
    - TDD passes: units 1 and 2 run tests first; unit 5 is a dependency move proven by the existing suite on a 2.0 overlay before the change and in `make ci` after it
* Insights
    - Gate 4a and the N5 red command have a path slip (`--project skills/sr-search` from the engine dir fails in uv 0.12.22); use the `uv --directory skills/sr-search` form
    - Step 5.1 needs a step for a live-file change after gate 4b, or the baseline stops being a rollback copy; `stockroom doctor smoke` is a third nanobind-exposed `BgeEncoder` path that nothing checks

## 2026-10-22 - REVIEW (OPERATOR) - COMPLETE

* Work completed
    - Made the backup the operator asked for before the build: `~/.local/share/stockroom/warehouse.issue147-pre-duckdb2.duckdb`, a byte copy under the writer flock with no `.wal`, SHA-256 equal to the live file
    - Folded the operator's decisions on the nine preflight advisories into `tasks.md` and `projectbrief.md`
* Decisions made
    - Operator: adopt advisories 1, 2, 4, 5, 6, and 7; leave 3 (the "can be deleted" line stays); major version release (advisory 8, `feat!:`); decline the worktree idea (9)
    - Operator: every backup stockroom or a contributor makes is named `warehouse.issue147-<purpose>.duckdb` in the stockroom home, so a later release that deletes backups when present removes only stockroom's own, never a user's
    - The named backup, not the shadow baseline, is the landing's rollback copy; the shadow scratch home is deleted after gate 4b
* Insights
    - Milestone 1 kept no backup of the live warehouse: its proof copies were deleted once the live migrate verified, which departs from the developer guide's "Make a Backup" step. The rows were verified intact, so nothing was lost, but there was no rollback copy

## 2026-10-22 - BUILD - COMPLETE

* Work completed
    - Step 1 (`fb09cf4`): the Hub-notice filter lives only for the model load; N1 to N5
    - Step 2 (`e011a53`): the shadow script's live-phase checks and milestone 1 QA cleanups; S1 to S6
    - Step 3: fresh-clone recipe smoke (`--synthetic`) passed without touching the live engine or warehouse
    - Gates: 4a (suite on the 2.0.0 overlay with torch) green; 4b (shadow run from the clone on a copy of the live warehouse) exit 0
    - Step 5 (`ac8c6ca`): `feat!: move the engine to DuckDB 2.0` (range, lock, Dependabot, doc page, techContext); `make ci` and the strict docs build green
    - Step 6: supervised live checks on DuckDB 2.0 all passed; DuckDB 1.5.4 still opens the live file
    - Step 7: `make ci` and the docs build green on the landed tree
* Decisions made
    - Accepted uv 0.12.22's lock-format rewrite with the duckdb bump; only duckdb changed in the package set
    - Did not chase the pytest-plus-torch nanobind exit noise: it is a test-process effect, not a stockroom command, and does not change any exit code
* Insights
    - The first live write under 2.0 was supervised, after both gates; the named backup was byte-identical to the live file up to that moment

## 2026-10-22 - QA - COMPLETE (PASS)

* Work completed
    - Semantic review of the build (`b0b4bc8..HEAD`) against the Level 3 plan, milestone 2's done list, and the brief. Checked the Hub-filter context manager and its wiring, N1 to N5, the shadow script's new checks and milestone-1 cleanups, S1 to S6, the range, lock, and Dependabot change, the doc page, `techContext`, and the commit shape (`feat!:`, `BREAKING CHANGE` footer, lock last)
    - Ran, with no sync, on the landed tree: pytest 1,050 passed and 39 skipped; ruff check and format-check on the engine and `scripts/`; `uv lock --locked`; and `make docs-build` (strict). All green
* Decisions made
    - PASS. Five advisories are recorded in `tasks.md`, and none blocks: a stale `test_embed.py` module docstring; "overlay" naming in the shadow script; the 2.0-lock run form not yet run end to end (the operator's Mac run, a release gate, covers it, and a failure there is loud); the pytest-plus-torch nanobind noise, recorded only in context; and torch stripped from `.venv` again by the QA-save commit's hook
* Insights
    - The lock's `revision` bump is safe for users on older uv: uv documents revision changes as backward compatible. The hashed torch freeze holds only the torch stack, so a heal cannot downgrade DuckDB
