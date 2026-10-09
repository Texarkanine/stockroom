# Progress

Determine whether Claude Code ingest overcounts token usage by storing each API response's usage on every content-block line, fix ingestion if that is a real bug, recompute sessions whose transcripts remain on disk, and rewrite vanished-transcript rows only when the correction is fully correct and idempotent.

**Complexity:** Level 2

## 2026-10-09 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - Restated the investigation, the ingest fix, and the vanished-transcript bar; the operator approved it
    - Classified the work as Level 2
* Decisions made
    - Level 2: a bug fix across Claude ingest, message identity, the session token rollup, and a possible warehouse correction, without an architecture change
* Insights
    - The report's approximate collapse of consecutive assistant rows does not meet the operator's bar for rewriting rows whose transcripts are gone

## 2026-10-09 - PLAN - COMPLETE

* Work completed
    - Confirmed `_build_message` copies each assistant line's `message.usage` and `session_token_usage` sums those columns
    - Wrote the Level 2 plan: attribute field-wise max once per API response, clear forked parent copies on subagents, document `ingest --full` for sessions still on disk
* Decisions made
    - No warehouse DML for transcripts that are gone
    - No schema migration; `api_message_id` and `request_id` stay parse-time fields the writer does not persist
    - Repro JSONL lives in `tmp_path` so the ingest golden corpus stays put
* Insights
    - Committed Claude fixtures put a whole content array on one line, which is why the overcount has no failing test today
