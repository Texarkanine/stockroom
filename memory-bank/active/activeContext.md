# Active Context

## Current Task: cursor-cli-and-entrypoint-ingest
**Phase:** COMPLEXITY-ANALYSIS - COMPLETE

## What Was Done
- Clarified intent: Cursor Agent CLI ingest + Claude `entrypoint` passthrough + `sessions.entrypoint`; no dashboard UI; Linux roots only
- Researched sources: `~/.cursor/chats/**/store.db` (CLI), `agent-transcripts` (IDE), Claude JSONL native `entrypoint` (`cli` / `claude-desktop`)
- Confirmed collision hypothesis on n=1: transcript detail ≤ store.db; prefer store.db
- Determined Level 3 (intermediate feature spanning discovery, parsers, schema, writer, dedup, tests)

## Next Step
- Load Level 3 workflow and execute plan phase
