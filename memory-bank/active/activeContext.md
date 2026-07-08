# Active Context

## Current Task: p3-m1-stockroom-dispatcher
**Phase:** PLAN - COMPLETE

## What Was Done
- Surveyed the four existing module CLIs: `query` / `semantic` / `embed` are single runnable modules with `main(argv) -> int`; `ingest` is a package with `__main__.py`; `migrate.py` is library-only (`ensure_schema_version_table` / `current_version` / `apply_pending`, no parser)
- Plan written to `tasks.md`: first-token dispatch in a new `stockroom/__main__.py` (lazy import, verbatim `argv[1:]` forwarding, exit-code passthrough), a new `migrate` CLI that opens through the `warehouse.open()` chokepoint (lazy gate migrates; reports `current_version`), README ad-hoc examples switched to `python -m stockroom <sub>`
- Test plan: two new subprocess-based CLI test files (`test_dispatcher_cli.py`, `test_migrate_cli.py`) following the `test_query_cli.py` convention; torch-dependent subcommands exercised via `--help` (exits before encoder construction)

## Next Step
- Preflight validation (runs automatically)
