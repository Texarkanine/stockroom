# Project Brief

## User Story

As a stockroom operator on WSL with a Windows Cursor install, I want Cursor model enrichment to find the real `ai-code-tracking.db` and read the current schema so that `sessions.models` (and a subsequent `--full` Cursor re-ingest) populate warehouse facts the dashboard can show.

## Use-Case(s)

### Use-Case 1

Unconfigured Cursor ingest on a WSL+Windows machine resolves the live enrichment DB, reads models from the current table shape, and writes non-empty `sessions.models` for overlapping conversations.

### Use-Case 2

After the code fix, the operator runs `stockroom ingest --full --harness cursor` and sees previously missing model (and any re-ingest-backed date/observation) fields populate in the warehouse.

### Use-Case 3

When the DB or expected tables are absent, enrichment still returns `{}` without raising.

## Requirements

1. Resolve the enrichment DB via `STOCKROOM_AI_TRACKING_DB`, then candidate search: `~/.cursor/ai-tracking/ai-code-tracking.db`, legacy `~/.cursor/ai-code-tracking.db`, and WSL `/mnt/<drive>/Users/*/.cursor/ai-tracking/ai-code-tracking.db` (first existing file wins).
2. Read model rows from the current Cursor schema (at least `ai_code_hashes.model`, optionally `conversation_summaries.model`), keyed by conversation id, de-duplicated in first-seen order.
3. Keep graceful empty results when the DB/table is absent or the schema is unknown.
4. Update the synthetic fixture/tests and stale "DB is absent on this machine" comments.
5. Focused enrich/orchestrator tests cover path resolution and the new table shape.
6. After the code fix, verify with `stockroom ingest --full --harness cursor` that warehouse sessions gain the missing model data.

## Constraints

1. Dashboard-only workarounds are out of scope (dashboard stays read-only over warehouse facts).
2. Attribution tables beyond the model grain stay out of scope.
3. Canonical engine lives under `skills/sr-search/` (`.cursor/skills/stockroom-local/sr-search` is a symlink).

## Acceptance Criteria

1. Unconfigured ingest on a WSL+Windows Cursor install finds the real DB and populates `sessions.models` for overlapping conversations.
2. Absent DB / unknown schema still no-ops without error.
3. Focused enrich/orchestrator tests cover path resolution and the new table shape.
4. Operator can run `stockroom ingest --full --harness cursor` and observe previously missing model data (and re-ingest-backed date/observation fields) in the warehouse.
