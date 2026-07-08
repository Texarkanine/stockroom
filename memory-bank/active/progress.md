# Progress

Milestone m1 of L4 project `p3-onboarding-cli-scheduling`: build the tested `python -m stockroom` dispatcher — a new `src/stockroom/__main__.py` dispatching `query` / `semantic` / `ingest` / `embed` / `migrate` to the existing module CLIs, authoring the currently-missing `stockroom.migrate` CLI entrypoint, with top-level `--help` listing subcommands, `stockroom <sub> --help` forwarding to each module's argparse, and README dispatcher documentation. See `memory-bank/active/milestones.md` (m1) and `memory-bank/active/projectbrief.md`.

**Complexity:** Level 2

## 2026-07-08 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - `/niko` re-entry routed L4 project to first-milestone classification (Step 2 "Not started" → Step 7)
    - m1 classified as Level 2: self-contained new module over existing tested CLIs plus one small new argparse `main()` for `stockroom.migrate`
    - Sub-run ephemeral state written: fresh `progress.md`, updated `activeContext.md`, stubbed `tasks.md`; `projectbrief.md` and `milestones.md` preserved
* Decisions made
    - Level 2 classification, matching the milestone's estimate and the L4 preflight's scope amendments (migrate CLI entrypoint + README dispatcher docs are in-scope for m1)
* Insights
    - Dispatch shape is pre-specified in `planning/brainstorm/stockroom-on-path-cli.md`; the plan phase should treat it as the design input rather than re-deriving it

## 2026-07-08 - PLAN - COMPLETE

* Work completed
    - Codebase survey: `query`/`semantic`/`embed` are single runnable modules with `main(argv) -> int`; `ingest` is a package with `__main__.py`; `migrate.py` is library-only
    - Plan written to `tasks.md`: first-token dispatch in a new `stockroom/__main__.py` (lazy import, verbatim `argv[1:]` forwarding, exit-code passthrough); new migrate CLI opening through the `warehouse.open()` chokepoint; README examples switched to `python -m stockroom <sub>`
    - Test plan: two new subprocess-based CLI test files following the `test_query_cli.py` convention
* Decisions made
    - First-token dispatch instead of argparse subparsers — modules keep sole ownership of their flags, `--help` forwarding is free
    - Migrate CLI relies on the chokepoint's lazy gate (creates + migrates a missing warehouse) and reports `current_version`
    - Forwarded `--help` keeps module `prog` names — accepted cosmetic wrinkle; naming story belongs to m2
* Insights
    - Torch-dependent subcommands are testable torch-free via `--help` forwarding (both validate/exit before encoder construction)

## 2026-07-08 - PREFLIGHT - COMPLETE (PASS)

* Work completed
    - TDD encoding, convention compliance, dependency impact, conflict detection, and completeness verified against the codebase; `.preflight-status` written PASS
    - Verified `stockroom.migrate` consumers (`warehouse.py`, `conftest.py`, `_warehouse_worker.py`) import library functions only — the new CLI is purely additive
    - Verified REUSE coverage: engine `.py` files carry no inline SPDX headers; `REUSE.toml` path annotations cover the new files
* Decisions made
    - Amendment: dispatcher gains a top-level `--version` flag (prints `stockroom.__version__`) as a cheap identity probe for the m2 shim's staleness verification

## 2026-07-08 - BUILD - COMPLETE

* Work completed
    - `stockroom/__main__.py` dispatcher implemented (first-token dispatch, lazy imports, verbatim forwarding, `--help`/`--version`, exit-code passthrough)
    - `stockroom.migrate` CLI implemented (`_build_parser`/`main` over the `warehouse.open()` chokepoint; bootstrap-on-missing; clean `WarehouseBusyError` handling)
    - 11 new subprocess tests (8 dispatcher, 3 migrate) written red-first, all green; README ad-hoc examples switched to `python -m stockroom <subcommand>`
    - `make ci` fully green: lint, format, 277 passed / 2 torch-gated skips, REUSE compliant
* Decisions made
    - `warehouse` imported inside `migrate.main` to break the load-time circularity (`warehouse.py` imports `stockroom.migrate`)
    - Help-forwarding tests fingerprint each module by a unique flag/phrase, keeping torch-heavy subcommands exercised torch-free
* Insights
    - The dispatcher needed zero changes to any module CLI — the uniform `main(argv) -> int` shape across modules made wrapping trivial

## 2026-07-08 - QA - COMPLETE (PASS)

* Work completed
    - Semantic review against the plan: KISS/DRY/YAGNI/completeness/regression/integrity all clean — no over-engineering, no speculative code, no debris, every planned behavior implemented and tested
    - Two trivial documentation gaps fixed in QA: `migrate.py` module docstring now states the module is runnable; `memory-bank/techContext.md` gained a "CLI dispatcher" section (the persistent-doc counterpart of the README update)
    - `make ci` re-run after fixes: fully green (277 passed / 2 torch-gated skips, REUSE compliant)
    - `.qa-validation-status` written: PASS

## 2026-07-08 - REFLECT - COMPLETE

* Work completed
    - Reflection document written (`reflection-p3-m1-stockroom-dispatcher.md`): delivered to plan, first-pass green through preflight/build/QA; one preflight-amended addition (`--version`)
    - Persistent files reconciled — `techContext.md` dispatcher section landed in QA; no other persistent file invalidated
* Insights
    - Uniform `main(argv) -> int` module-CLI shape keeps dispatcher additions one-line table entries — preserve it for future modules (m3 `doctor` advisory)
    - `warehouse.py` → `stockroom.migrate` load-time import means migrate-side CLI code imports `warehouse` lazily; same cycle awaits any warehouse-imported module that grows a CLI
