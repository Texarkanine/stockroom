# Active Context

## Current Task: doctor-smoke-ensure-env-remedy
**Phase:** BUILD - COMPLETE

## What Was Done
- Freeze-aware missing-torch remedy in `run_smoke` via `read_freeze_path()`
- Unit tests: no-freeze / usable-freeze / unusable-freeze; CLI assertion branches on freeze
- Docs: `docs/user-guide/troubleshooting/torch.md` doctor-smoke bullet
- Verification: `make format && make lint && make test` — 671 passed, 4 skipped

## Files modified
- `/home/mobaxterm/.cursor/worktrees/doctor-smoke-b1ed7471/stockroom-82a30ca4ee38/skills/sr-search/src/stockroom/doctor.py`
- `/home/mobaxterm/.cursor/worktrees/doctor-smoke-b1ed7471/stockroom-82a30ca4ee38/skills/sr-search/tests/test_doctor.py`
- `/home/mobaxterm/.cursor/worktrees/doctor-smoke-b1ed7471/stockroom-82a30ca4ee38/skills/sr-search/tests/test_doctor_cli.py`
- `/home/mobaxterm/.cursor/worktrees/doctor-smoke-b1ed7471/stockroom-82a30ca4ee38/docs/user-guide/troubleshooting/torch.md`

## Key decisions
- Gate on `read_freeze_path()` only (same as `ensure_torch`)
- Freeze-present remedy: `stockroom shim ensure-env` (+ optional `sr-initialize` re-pick); no raw `uv pip install torch`

## Next Step
- QA review (automatic for Level 2)
