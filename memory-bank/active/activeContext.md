# Active Context

## Current Task: fix-plugin-env-heal-after-move
**Phase:** BUILD - COMPLETE (rework: torch persistence)

## What Was Done
- Durable `{stockroom_home}/torch-index`; `torch_source.ensure_torch`; wired into `ensure_engine_env`
- CLI `stockroom torch record`; `sr-initialize` + `make torch` write the record
- Hook timeout 300s for cold torch wheels
- Full suite: 445 passed, 3 skipped

## Next Step
- QA / reflect for rework, then `/niko-archive`
