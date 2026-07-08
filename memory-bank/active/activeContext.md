# Active Context

## Current Task: p3-m2-stockroom-shim
**Phase:** BUILD - COMPLETE

## What Was Done
- All 8 plan steps built TDD (red → green each):
  - New: `src/stockroom/shim_template.sh` (POSIX-sh, baked-only, succeed-or-refuse), `src/stockroom/shim.py` (render/install/rectify + CLI), `hooks/cursor-hooks.json`, `hooks/claude-hooks.json`, `tests/test_shim.py` (17), `tests/test_shim_runtime.py` (6), `tests/test_shim_cli.py` (7)
  - Modified: `REUSE.toml` (`skills/**/*.sh` AGPL re-assert), `__main__.py` (sixth `SUBCOMMANDS` row `shim`), both plugin manifests (`"hooks"` pointers), `Makefile` (`shim` target, no `sync` dep so torch survives), `README.md` (ad-hoc section rewritten around `stockroom <subcommand>`; raw incantation demoted to a bootstrap footnote), `tests/{conftest,test_dispatcher_cli,test_licensing,test_packaging}.py`, `memory-bank/{techContext,systemPatterns}.md` (shim section; hook-discipline amendment)
- Key build decisions (not in creative docs):
  - Remedy strings must stay free of shell-active chars (backticks in the dev remedy were executed by the rendered script's double-quoted `echo` — caught by the runtime test)
  - `shim.py` CLI is a flat parser (positional `install|rectify` + shared flags), not argparse subparsers — one help page, matches the "module owns its flags" convention
  - Licensing DID gain a cheap test (`test_shell_inside_skill_resolves_agpl`) beyond the plan's "inspection only" stance
  - Claude hook `timeout` is seconds (10), Cursor's is ms (10000) — per each harness's schema
- Integration results: full suite 311 passed / 2 skipped (torch-gated, expected); `make ci` fully green (lock-check, ruff lint+format, pytest, `reuse lint` 190/190 compliant)

## Next Step
- QA phase (`niko-qa` runs automatically after build)
- QA artisanal checklist (from preflight): live hook firing needs a real plugin install — `make localdev` mirrors only `skills/`, so plugin-delivered hooks won't fire from a localdev mirror
