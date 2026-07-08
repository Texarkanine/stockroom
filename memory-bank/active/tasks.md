# Task: `stockroom` dispatcher (`python -m stockroom`)

* Task ID: p3-m1-stockroom-dispatcher
* Complexity: Level 2
* Type: simple enhancement (new CLI entrypoint over existing tested surfaces)

Milestone m1 of L4 project `p3-onboarding-cli-scheduling`. A new `skills/sr-search/src/stockroom/__main__.py` makes `python -m stockroom` behave like a CLI with subcommands: `stockroom query …` dispatches to `stockroom.query`, likewise `semantic` / `ingest` / `embed` / `migrate`. `stockroom.migrate` is library-only today, so m1 also authors its missing CLI entrypoint. Top-level `--help` lists the subcommands; `stockroom <sub> --help` forwards to each module's existing argparse. The dispatcher **wraps** the module CLIs (calls their `main(argv)`), never reimplements them — module CLIs remain unchanged public surfaces. README gains dispatcher documentation.

Design input: `planning/brainstorm/stockroom-on-path-cli.md` → "The dispatcher". The m2 shim will exec `python -m stockroom "$@"`, so the dispatch surface built here is the one the on-path `stockroom` command exposes verbatim.

## Design Decisions

- **First-token dispatch, verbatim forwarding.** The dispatcher inspects `argv[0]`: if it names a known subcommand, lazily import that module and call its `main(argv[1:])`, returning its exit code unchanged. No argparse subparsers duplicating module flags, no `REMAINDER` quirks — each module's own argparse handles everything after the subcommand token, so `<sub> --help` forwarding is free and module CLIs stay the single source of truth for their flags.
- **Lazy per-subcommand import.** The target module is imported only after dispatch resolves, so `stockroom --help` / error paths stay fast and dispatch never eagerly pulls a heavy module chain.
- **Top-level contract**: `--help` / `-h` → usage listing the five subcommands on stdout, exit 0. No args → usage to stderr, exit 2. Unknown subcommand → one-line error naming the bad token + usage hint to stderr, exit 2 (argparse's conventional bad-usage code).
- **`stockroom.migrate` CLI** (new `main()` / `_build_parser()` / `__main__` guard in `migrate.py`, mirroring the `query.py` single-runnable-module shape): opens the warehouse read-write through the `warehouse.open()` chokepoint — the lazy migration gate inside `open()` performs any pending migration, preserving the "all surfaces go through the chokepoint" invariant — then reports `current_version` and exits 0. A missing warehouse is *created and migrated to head* (bootstrapping the schema is the point of an explicit migrate). `WarehouseBusyError` → clean stderr message, exit 1, no traceback.
- **Known cosmetic wrinkle, accepted**: forwarded `--help` output shows each module's existing `prog` (`python -m stockroom.query` etc.). Renaming progs would touch the unchanged public surfaces for cosmetics; the m2 shim milestone owns the user-facing naming story.

## Test Plan (TDD)

### Behaviors to Verify

Dispatcher (`tests/test_dispatcher_cli.py`, subprocess-based per existing CLI-test convention):

- Top-level help: `python -m stockroom --help` → exit 0, stdout lists all five subcommands (`query`, `semantic`, `ingest`, `embed`, `migrate`)
- Version: `python -m stockroom --version` → exit 0, prints `stockroom.__version__` (preflight amendment: gives the m2 shim and later `doctor` a cheap identity probe)
- No args: `python -m stockroom` → exit 2, usage on stderr
- Unknown subcommand: `python -m stockroom bogus` → exit 2, stderr names `bogus`, no traceback
- Help forwarding: `python -m stockroom query --help` → exit 0, output shows `stockroom.query`'s own flags (e.g. `--format`, `--detail`); same for `semantic` / `ingest` / `embed` / `migrate` (each identified by a module-unique help string; `--help` exits before encoder construction, so the torch-dependent subcommands are exercised torch-free)
- Real dispatch: `python -m stockroom query "SELECT 1 AS n"` against an ingested throwaway `STOCKROOM_HOME` → exit 0, same TSV output as `python -m stockroom.query`
- Exit-code propagation: `python -m stockroom query "   "` → exit 2 (module's empty-SQL code, unchanged); `python -m stockroom query "SELECT 1"` with no warehouse → exit 1 with the module's "run ingest first" hint

Migrate CLI (`tests/test_migrate_cli.py`, subprocess-based):

- Fresh home: `python -m stockroom.migrate` with empty `STOCKROOM_HOME` → exit 0, warehouse file created, output reports the head schema version
- Idempotence: second run against the same home → exit 0, same version reported, no error
- Help: `python -m stockroom.migrate --help` → exit 0, description mentions migration
- Via dispatcher: `python -m stockroom migrate` on a fresh home → exit 0, warehouse created (locks the dispatch wiring end-to-end)

Edge cases covered: no args (empty state), unknown token (invalid input), `--help` on every subcommand (boundary of the forwarding contract), exit-code propagation (regression guard on the wrapped modules' contracts), migrate-on-missing-warehouse (bootstrap boundary).

### Test Infrastructure

- Framework: pytest, configured in `skills/sr-search/pyproject.toml` (`pythonpath = ["src"]`)
- Test location: `skills/sr-search/tests/`
- Conventions: CLI surfaces get end-to-end subprocess tests (`test_query_cli.py`, `test_ingest_cli.py` precedent): `sys.executable -m …` with `PYTHONPATH` + `STOCKROOM_HOME` env, fixture roots from `conftest.py` where a populated warehouse is needed
- New test files: `tests/test_dispatcher_cli.py`, `tests/test_migrate_cli.py`

## Implementation Plan

All steps completed 2026-07-08 (build phase).

1. Stub the interface (TDD preparation)
   - Files: `skills/sr-search/src/stockroom/__main__.py` (new), `skills/sr-search/src/stockroom/migrate.py`
   - Changes: `__main__.py` with documented `main(argv: list[str] | None = None) -> int` stub, the subcommand table, and the `if __name__ == "__main__"` guard; `migrate.py` gains documented stubs for `_build_parser()` / `main(argv)` and the `__main__` guard. Stub `tests/test_dispatcher_cli.py` / `tests/test_migrate_cli.py` with empty, docstring-described test cases.
2. Write the migrate-CLI tests, then implement `migrate.main`
   - Files: `skills/sr-search/tests/test_migrate_cli.py`, `skills/sr-search/src/stockroom/migrate.py`
   - Changes: implement the four migrate behaviors as failing tests; then fill in `_build_parser` (prog `python -m stockroom.migrate`) and `main` (chokepoint open → report `current_version` → close; `WarehouseBusyError` → clean stderr, exit 1)
3. Write the dispatcher tests, then implement `__main__.main`
   - Files: `skills/sr-search/tests/test_dispatcher_cli.py`, `skills/sr-search/src/stockroom/__main__.py`
   - Changes: implement the six dispatcher behaviors as failing tests; then fill in first-token dispatch with lazy imports, the usage text, and exit-code passthrough
4. README dispatcher documentation
   - Files: `README.md`
   - Changes: in the ad-hoc-invocation section, introduce `python -m stockroom <subcommand>` as the dispatch surface (subcommand list + `--help` discipline) and switch the two examples to `python -m stockroom ingest --full` / `python -m stockroom query "…"`; the surrounding `PYTHONPATH`/uv incantation stays (its removal is m2's shim rewrite)
5. Full verification
   - Files: n/a
   - Changes: `make ci` (lint, format-check, full pytest suite, reuse lint — new source files are covered by the existing `REUSE.toml` path annotations; verify `reuse lint` agrees)

## Technology Validation

No new technology - validation not required (stdlib `argparse` + existing project tooling only).

## Dependencies

- Existing module CLIs (`stockroom.query`, `stockroom.semantic`, `stockroom.embed`, `stockroom.ingest.__main__`) — wrapped unchanged
- `stockroom.warehouse.open()` chokepoint + `stockroom.migrate.current_version` for the migrate CLI
- Test fixture roots in `tests/conftest.py` (`cursor_root`, `claude_root`, `ai_tracking_db`) for the populated-warehouse dispatch test

## Challenges & Mitigations

- Forwarded `--help` shows module `prog` names, not `stockroom <sub>`: accepted cosmetic wrinkle (documented above); renaming is deferred to the m2 shim's naming story rather than touching unchanged surfaces
- Torch-dependent subcommands (`semantic`, `embed`) in dispatcher tests: exercise via `--help` forwarding only — both modules validate/exit before `encoder_factory()` runs, so no torch is needed in CI
- `stockroom migrate` under a concurrently-held write lock: `warehouse.open` already degrades to `WarehouseBusyError`; the CLI translates it to a clean message (no traceback), matching the query CLI's error discipline
- Dispatcher must not shadow `python -m stockroom.ingest`: adding `__main__.py` to the package does not affect `python -m stockroom.<module>` resolution (verified in L4 preflight)

## Preflight Findings (2026-07-08, PASS)

- TDD encoding verified: steps 1–3 order stub → failing tests → implementation per unit (migrate CLI, then dispatcher).
- Convention compliance verified: `__main__.py` mirrors the `ingest` package precedent; the migrate CLI mirrors the `query.py` single-runnable-module shape; subprocess tests match the `test_query_cli.py` convention; new `.py` files are already AGPL-covered by `REUSE.toml` path annotations (no inline headers needed — no existing engine `.py` carries one).
- Dependency impact verified: all existing `stockroom.migrate` consumers (`warehouse.py`, `conftest.py`, `_warehouse_worker.py`) import library functions only — adding `main()`/`_build_parser()` is purely additive.
- Conflict check verified: no existing `stockroom/__main__.py`; the migrate CLI wraps the `warehouse.open()` chokepoint (whose lazy gate already migrates) rather than duplicating runner logic.
- **Amendment**: top-level `--version` flag added to the dispatcher contract (prints `stockroom.__version__`, exit 0) — cheap identity probe for the m2 shim's staleness verification.

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Preflight (PASS)
- [x] Build (all 5 steps; `make ci` green: 277 passed, 2 torch-gated skips, REUSE compliant)
- [ ] QA
