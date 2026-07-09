# Active Context

## Current Task: fix-cursor-model-enrichment
**Phase:** BUILD - COMPLETE

## What Was Done
- Fixed `stockroom.ingest.enrich` path resolution (env → modern → legacy → WSL mounts) and schema read (`ai_code_hashes` + optional `conversation_summaries`)
- Updated synthetic fixture/tests/docs; full suite green
- Left live `--full` Cursor re-ingest to the operator

## Next Step
- QA phase (`/niko-qa`)
