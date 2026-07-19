# Project Brief

## User Story

As a stockroom user, I want harness-reported token usage stored and easy to roll up at conversation grain so that I can analyze spend/usage from Claude Code today without locking out future harnesses that only report session-level totals.

## Use-Case(s)

### Query message-level tokens (Claude Code)

Claude Code already exposes per-assistant-message usage. I can sum or filter those fields via `sr-query` without inventing values Cursor does not provide.

### Easy conversation rollups

I can get per-session token totals cheaply and idiomatically (without awkward ad-hoc SQL or expensive rework later).

### Future session-grain harness

When a harness reports conversation-level usage only, stockroom can store that without a painful migration or fabricating per-message splits.

## Requirements

1. Keep Claude Code message-grain tokens as the source of truth for that harness (`input` / `output` / cache create / cache read).
2. Do not attribute Cursor usage from dashboard CSV/API into sessions/messages — Cursor does not expose joinable token data.
3. Make conversation-level rollups easy to query for message-grain sources.
4. Leave a clear, cheap path for future session-grain token reporting (schema/query design must not force an expensive migration when that arrives).
5. Preserve "one meaning per field": never invent message-level tokens from session totals.

## Constraints

1. Dual-harness warehouse; Cursor columns may stay NULL.
2. Forward-only migrations; avoid cornering the schema.
3. Local-only core product; no requirement to build a Cursor CSV/API enricher in this task.
4. Follow existing harness-labeled schema and ingest patterns.

## Acceptance Criteria

1. Claude message token fields remain correctly ingested and queryable.
2. A documented, easy path exists to obtain per-session token rollups from message-grain data.
3. Schema (and any ingest hooks) can accept future session-grain token totals without a destructive/expensive migration.
4. Tests cover rollup ergonomics and any schema/ingest changes.
5. Cursor continues to leave token fields NULL; no false attribution from external usage exports.
