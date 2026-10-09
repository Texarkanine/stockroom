---
task_id: claude-token-overcount
complexity_level: 2
date: 2026-10-09
status: completed
---

# TASK ARCHIVE: claude-token-overcount

## SUMMARY

Claude Code writes one transcript line per content block and repeats that response's `message.usage` on every line. Ingest copied those counts onto every kept assistant row, and `session_token_usage` summed them, so a multi-block response was counted about once per line. Ingest now keeps one row per line and stores the field-wise max once per `(message.id, requestId)`. A subagent line that repeats its parent's response id carries no tokens. Rows whose transcripts are gone stay as stored. Pull request [#138](https://github.com/Texarkanine/stockroom/pull/138) is open.

## REQUIREMENTS

1. Confirm the report against ingest, the schema, and the token rollup before changing code.
2. If the overcount is real, count each Claude API response once, including a forked subagent copy of the parent response.
3. Sessions whose transcripts are still on disk can be brought in line by re-ingest.
4. Rewrite vanished-transcript rows only when the correction is fully correct and idempotent. An approximate collapse does not qualify.

## IMPLEMENTATION

No schema migration. `api_message_id` and `request_id` are parse-time fields on `NormalizedMessage`; the writer does not persist them, and `session_token_usage` is still a `SUM`.

`_attribute_response_usage` groups assistant lines by `(message.id, requestId)` when both are non-empty strings. The last line of the group keeps the field-wise max of the four counts; the other lines in the group store `NULL`. Lines missing either id keep their own tokens. `drop_copied_parent_usage` clears the four token fields on a subagent message whose pair is already on the parent. Text and tool calls stay on their own rows.

The report's three-line fixture sums to `(6, 3000, 150000, 136)` before the fix and `(2, 1000, 50000, 120)` after. Repro JSONL is built in `tmp_path` so the ingest golden corpus stays put. Committed fixtures put a whole content array on one line, which is why the overcount had no failing test.

Docs: the warehouse architecture page states the once-per-response rule, and the ingest page states that `stockroom ingest --full` (or `--harness claude`) rewrites sessions whose transcripts remain. Vanished rows are called out in those pages, the Claude parser docstring, and the pull request body.

Key files: `skills/sr-search/src/stockroom/ingest/claude.py`, `skills/sr-search/src/stockroom/ingest/model.py`, `skills/sr-search/src/stockroom/ingest/__init__.py`, `skills/sr-search/tests/test_ingest_claude.py`, `skills/sr-search/tests/test_ingest_orchestrator.py`, `docs/architecture/warehouse.md`, `docs/user-guide/load/basic.md`.

## TESTING

- TDD on the parser and the orchestrator: multi-block once, field-wise max when the last line is lower, two distinct responses, missing identity left unmerged, user and empty usage stay `NULL`, re-parse is stable, `write_session` rollup is `(2, 1000, 50000, 120)` with `token_grain = message`, and a forked subagent copy does not add the parent's tokens.
- Targeted ingest tests after QA: 76 passed across `test_ingest_claude.py`, `test_ingest_orchestrator.py`, and `test_ingest_writer.py`.
- Full engine run: 888 passed, 4 skipped, 1 failed. The failure is `test_docs_lock_is_not_stale` on this machine's uv 0.8.22 against the committed root lock, independent of this change. Dashboard JS: 134 passed. Lint, format check, schema-docs check, and reuse lint passed.
- Preflight PASS WITH ADVISORY. QA PASS, no required fixes. Advisory only: token columns sit on one row of the group, which is the intended tradeoff so the golden snapshot stays put.
- Surviving transcripts (2026-10-06 through 2026-10-09; 721 responses, 1,629 usage lines) match a consecutive `(input, cache_creation, cache_read)` collapse to `(message.id, requestId)` exactly, including the four token totals. No cache triple belongs to two API responses. `stockroom ingest --full --harness claude` has not been run on this machine.

## LESSONS LEARNED

### Technical

`output_tokens` on earlier lines of one response is a partial, so the stored count is the field-wise max, not the last line and not a sum. Corpus fixtures that put one content array on one line cannot catch a per-line usage copy. Without `message.id` and `requestId` on old rows, a repeated response cannot be told from two responses that share a cache triple. A user row or a multi-minute gap between equal triples also occurs inside one response, so those shapes are not a stand-in for the missing ids.

### Process

A repair within about 1% of a sample is still the wrong repair when the bar is exact and idempotent. The sample error was the reason to refuse a warehouse rewrite, not a reason to ship it with a flag.

### Million-dollar question

If response identity had been a warehouse column from the first Claude ingest, the view could sum each `(message.id, requestId)` once and prefer the parent, and vanished sessions would repair exactly. Those ids were never stored. Attributing once at parse time and leaving `SUM` alone is the fix that does not invent them.

## PROCESS IMPROVEMENTS

None. Plan, preflight, build, QA, and reflect held. The refusal of vanished-row DML was in the brief and did not have to be rediscovered in build.

## TECHNICAL IMPROVEMENTS

Preflight noted that coalescing every assistant block that shares `(message.id, requestId)` into one message row would remove the NULL-token siblings and match Cursor's one-turn-one-row grain. That would change Claude message counts and the golden snapshot in `tests/fixtures/ingest/expected_rows.json`. It was left alone. The once-per-response rule stays in the Claude parser and the architecture page. It is not a system-wide pattern beyond the view's existing `SUM`.

## NEXT STEPS

Finish [#138](https://github.com/Texarkanine/stockroom/pull/138). After merge, `stockroom ingest --full --harness claude` rewrites sessions whose transcripts are still on disk. Do not rewrite vanished-transcript rows, and do not wait on a check that names the merged pairs: June–September usage rows are still in the warehouse, their transcripts are gone, and the pairs cannot be named from what remains.
