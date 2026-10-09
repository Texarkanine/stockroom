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

## 2026-10-09 - PREFLIGHT - COMPLETE

* Work completed
    - Validated Level 2 implementation plan against codebase reality and TDD requirements
    - Verified TDD phase ordering across executable units 1 and 2
    - Verified architectural compliance with DuckDB schema, views, and writer isolation
    - Recorded Radical Innovation advisory finding regarding turn-level message coalescing
* Decisions made
    - Approved implementation plan as PASS WITH ADVISORY (advisory finding does not block build)
    - Proceeding to BUILD phase
* Insights
    - Ephemeral dataclass provenance avoids unnecessary schema migrations while enabling orchestrator-level subagent deduplication

## 2026-10-09 - BUILD - COMPLETE

* Work completed
    - Attributed Claude token counts once per `(message.id, requestId)`, field-wise max on the last line of the group
    - Cleared token columns on subagent rows that repeat a parent response id
    - Documented the count and that `ingest --full` rewrites sessions whose transcripts remain
    - Engine tests: 888 passed, 4 skipped, 1 failed (`test_docs_lock_is_not_stale` on this machine's uv 0.8.22). Dashboard JS: 134 passed. Lint, format check, schema-docs check, and reuse lint passed.
* Decisions made
    - No schema migration and no UPDATE of rows whose transcripts are gone
* Insights
    - The report's three-line fixture sums to `(6, 3000, 150000, 136)` before the fix and `(2, 1000, 50000, 120)` after

## 2026-10-09 - QA - COMPLETE (PASS)

* Work completed
    - Semantically reviewed the build against the plan across KISS, DRY, YAGNI, completeness, regression, integrity, and documentation; no blocking findings
    - Re-ran targeted ingest tests: 76 passed across `test_ingest_claude.py`, `test_ingest_orchestrator.py`, and `test_ingest_writer.py`
    - Wrote validation status to `memory-bank/active/.qa-validation-status` and marked QA complete in `tasks.md` / `activeContext.md`
* Decisions made
    - PASS with no required fixes; advisory only on the intended asymmetric per-row token placement
* Insights
    - Parse-time-only provenance fields kept the persistence boundary clean: writer INSERT lists and VIEW `session_token_usage` needed no changes

## 2026-10-09 - REFLECT - COMPLETE

* Work completed
    - Wrote `memory-bank/active/reflection/reflection-claude-token-overcount.md`
    - Left product context, system patterns, and tech context unchanged
* Decisions made
    - The once-per-response rule stays in the Claude parser and the architecture page. It is not a system-wide pattern beyond the view's existing SUM.
* Insights
    - Corpus fixtures that put one content array on one line cannot catch a per-line usage copy. Vanished rows cannot be repaired exactly because they never stored API identity.

## 2026-10-09 - PR - OPEN

* Work completed
    - Opened draft pull request 138, `fix(ingest): count each Claude API response's tokens once`, from `claude-code-doublecount`
* Decisions made
    - Left `.cursor/skills/stockroom-local/` untracked

