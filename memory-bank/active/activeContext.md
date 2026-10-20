# Active Context

## Current Task: torch-failures-help
**Phase:** BUILD - COMPLETE

## What Was Done
- `encoder_construction_error` in `skills/sr-search/src/stockroom/embed.py` turns an encoder-construction failure into one stderr line. `semantic.main` and `embed.main` print it and return 1. Other `ModuleNotFoundError` values still propagate.
- `missing_torch_remedy` and `encoder_load_remedy` are the clauses `doctor.run_smoke` already printed. Smoke now calls them.
- `skills/sr-semantic/SKILL.md`, `skills/sr-search/references/system-model.md`, `docs/user-guide/troubleshooting/torch.md`, and `docs/user-guide/load/basic.md` state the same three-way split.
- `make ci` passed: ruff, 1018 pytest passed (38 skipped), dashboard JS, reuse.

## Key decisions during build
- Did not add an optional `app_dir` argument. The quoting test monkeypatches `embed.default_app_dir`, which is the same pattern `doctor` tests use.
- Also edited `docs/user-guide/load/basic.md`. It quoted the old torch-page heading.

## Next Step
- QA review.
