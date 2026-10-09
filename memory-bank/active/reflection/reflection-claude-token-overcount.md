---
task_id: claude-token-overcount
date: 2026-10-09
complexity_level: 2
---

# Reflection: claude-token-overcount

## Summary

Claude Code token totals were counting each API response once per content-block line. Ingest now keeps one row per line and stores the field-wise max once per `(message.id, requestId)`, including clearing a subagent copy of its parent's response. That succeeded. Rows whose transcripts are gone were left as stored.

## Requirements vs Outcome

The investigation confirmed the report. New ingestion of a split response counts that response once, and a forked subagent copy does not add the parent's tokens again. Sessions still on disk are corrected by the existing `ingest --full` path. No warehouse rewrite was added for vanished transcripts, because a consecutive-triple collapse is not exact and those rows have no API identity to dedupe on.

## Plan Accuracy

The plan's files, order, and refusal of vanished-row DML held. The challenges that mattered showed up as predicted: corpus fixtures hide the bug because they put a whole content array on one line, and "keep the last line" would have been the wrong output rule. Nothing in the plan had to be reordered or dropped.

## Build & QA Observations

The three tests that encode the overcount failed on the old parser with the report's own numbers, then passed. QA passed with no fixes. The only red in the full engine run was `test_docs_lock_is_not_stale`, from this machine's uv 0.8.22 against the committed root lock, not from this change.

## Insights

### Technical

- Claude Code writes one transcript line per content block and repeats `message.usage` on each. `output_tokens` on earlier lines is a partial, so the count is the field-wise max. Stockroom's committed fixtures do not split lines, so a corpus golden cannot catch this.
- Without `message.id` and `requestId` stored on old rows, no later read can tell a repeated response from two responses that happen to share a cache triple. A user row or a time gap between equal triples also occurs inside one response, so those shapes are not a stand-in for the missing ids. On the transcripts still on disk (2026-10-06 through 2026-10-09; 721 responses) the consecutive-triple collapse matches the API identity exactly, including token totals. The report's roughly 1% gap was in transcripts that are now gone.

### Process

- A repair that is within 1% of a sample is still the wrong repair when the bar is exact and idempotent. The sample error was the reason to refuse it, not a reason to ship it with a flag.

### Million-Dollar Question

If response identity had been a warehouse column from the first Claude ingest, the view could sum each `(message.id, requestId)` once and prefer the parent, and that would repair vanished sessions exactly. We cannot invent those ids for rows that never stored them. Given the schema we have, attributing once at parse time and leaving `SUM` alone is the fix that does not pretend.
