# Active Context

## Current Task: torch-failures-help
**Phase:** BUILD - COMPLETE

## What Was Done
- `start_encoder` in `skills/sr-search/src/stockroom/embed.py` builds the encoder. A missing `torch` import with a usable hashed freeze prints `restoring torch from the hashed freeze`, calls the healer once (`ensure_engine_env` unless a test injects one), and retries once when the report action is not `failed`.
- `semantic.main` and `embed.main` take `healer` and return 1 when `start_encoder` returns `None`.
- No freeze and any other construction failure print one stderr line naming `sr-initialize`. `missing_torch_remedy` and `encoder_load_remedy` no longer name a pip command or a wheel index.
- `doctor.run_smoke` stays report-only. A usable freeze still names `stockroom shim ensure-env`.
- Skill, system model, torch page, and the embed section of the load guide match that behavior.

## Key Decisions
- Retry on any report that is not `failed`, including `noop`. Adopted the preflight advisory. The plan text said `synced` only.
- Call `importlib.invalidate_caches()` before the retry. Adopted the preflight advisory.
- Did not extract a generic `with_resilient_env` wrapper. That preflight advisory stays rejected.

## Deviations
- The new tests were in the tree before the restore behavior, and the first pytest run of them was already green. There is no captured red run.

## Next Step
- QA review (`/niko-qa`).
