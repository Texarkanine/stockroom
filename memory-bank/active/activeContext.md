# Active Context

## Current Task: fix-plugin-env-heal-after-move
**Phase:** BUILD - COMPLETE (hashed torch freeze rework)

## What Was Done
- Freeze API: `freeze_torch` / `read_freeze_path` / `torch-requirements.txt` + `torch-index` sidecar
- Heal: `ensure_torch` installs only via `--require-hashes -r` freeze (no floating index fallback)
- CLI: `stockroom torch freeze` (removed `record`); default `--app-dir` = engine
- Writers: `sr-initialize` install→smoke→freeze; `make torch` freezes; `docs/torch.md` + docs/patterns updates
- Verification: ruff clean; 456 passed, 3 skipped

## Files modified
- `skills/sr-search/src/stockroom/torch_source.py`
- `skills/sr-search/src/stockroom/torch_cli.py`
- `skills/sr-search/src/stockroom/engine_env.py`
- `skills/sr-search/src/stockroom/__main__.py`
- `skills/sr-search/tests/test_torch_source.py`
- `skills/sr-search/tests/test_torch_cli.py`
- `skills/sr-search/tests/test_torch_writers.py`
- `skills/sr-search/tests/test_dispatcher_cli.py`
- `Makefile`, `skills/sr-initialize/SKILL.md`
- `docs/torch.md`, `docs/development.md`, `docs/using.md`
- `memory-bank/systemPatterns.md`

## Key decisions
- Soft-fail reports for freeze/heal (no raise except bad index URL)
- Heal never uses index sidecar for resolve; freeze embeds indexes via `--emit-index-url`
- Legacy index-only homes must re-freeze once (no silent floating fallback)

## Deviations
- None — built to plan (plus preflight amendments)

## Next Step
- `/niko-qa` (auto-continue for L2)
