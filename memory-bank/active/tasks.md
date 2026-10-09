# Task: claude-token-overcount

* Task ID: claude-token-overcount
* Complexity: Level 2
* Type: bug fix

Claude Code writes one transcript line per content block of an API response, and every line repeats that response's `message.usage`. `stockroom.ingest.claude._build_message` copies those counts onto every kept assistant row, and VIEW `session_token_usage` sums `messages.*_tokens`. A multi-block response is therefore counted about once per line. Confirmed in `skills/sr-search/src/stockroom/ingest/claude.py` and migration `0007`. Committed fixtures put a whole content array on one line, so existing tests never see the split.

Fix attribution at ingest. Keep one `messages` row per kept line (text and tool calls stay per block). Within a session, group assistant lines by `(message.id, requestId)` and keep the field-wise max of the four counts on one row of the group; set the other rows' token columns to `NULL`. When a subagent transcript repeats a parent response's `(message.id, requestId)`, clear token columns on that subagent row. The view's `SUM` is then one response, once.

Sessions whose `.jsonl` is still on disk are corrected by the existing delete-then-insert writer when the operator runs `stockroom ingest --full` (optionally `--harness claude`). Incremental ingest will not revisit an unchanged parent mtime.

Do not rewrite warehouse rows whose transcripts are gone. Those rows have no `message.id` or `requestId`. Collapsing consecutive assistant rows that share an `(input, cache_creation, cache_read)` triple is approximate (the report's own check was about 1% on response count and 0.4% on tokens) and can merge two real responses. That is not fully correct, so it is out of scope even though a second run could be idempotent.


## Test Plan (TDD)

### Behaviors to Verify

- Multi-block response (the report's three lines: thinking, text, tool_use; output 8, then 8, then 120; shared `message.id` and `requestId`) → three assistant rows remain, text and the tool call stay on their lines, exactly one row keeps tokens, and the four sums are `(2, 1000, 50000, 120)`
- Field-wise max is not "last line wins": a later line with a lower `output_tokens` than an earlier line in the same `(message.id, requestId)` → the summed output is the max, not the last line
- Two assistant responses with different `(message.id, requestId)` → both responses' tokens are included in the sums
- Assistant lines missing `message.id` or `requestId`, even with identical usage → each line keeps its own tokens
- User rows → token columns stay `NULL`
- `parse_session` twice on the same file → the same token columns
- `write_session` of that multi-block session → `session_token_usage` totals equal `(2, 1000, 50000, 120)` and `token_grain` is `message`
- Subagent whose first assistant line repeats the parent's `(message.id, requestId)`, plus a later line of its own → parent totals unchanged, the copied subagent row has `NULL` tokens, and the subagent's own response is summed on that session
- Empty `usage` on an assistant line → token columns `NULL`, parse does not raise
- Existing one-line fixture turns → token columns unchanged (already covered by `test_per_message_model_and_token_columns`)

### Test Infrastructure

- Framework: pytest (engine `addopts` include xdist; override with `-n0` while iterating one test)
- Test location: `skills/sr-search/tests/`
- Conventions: one `test_` function per behavior, docstring stating the behavior; Claude fixtures are JSONL; `claude_root` / `migrated_con` come from `tests/conftest.py`; parser tests call `claude.parse_session`; warehouse tests call `writer.write_session` and read `session_token_usage`
- New test files: none

Build the new JSONL in `tmp_path`. Do not add it under `tests/fixtures/transcripts/claude/`. The orchestrator golden walks that tree.


## Implementation Plan

### 1. Attribute each Claude API response once — executable

- Files: `skills/sr-search/src/stockroom/ingest/claude.py`, `skills/sr-search/tests/test_ingest_claude.py`

1. Stub tests: add the six parser/view cases listed above (multi-block once, field-wise max when the last line is lower, two responses, missing identity, idempotent re-parse, view rollup) to `test_ingest_claude.py` with docstrings and empty bodies. The user-null and empty-usage cases are assertions inside the multi-block test, not extra suites.
2. Stub interface: add `_attribute_response_usage(messages: list[NormalizedMessage], keys: list[tuple[str, str] | None]) -> None` in `claude.py` with a docstring and an empty body. No writer or schema change.
3. Write tests and run red: multi-block fixture shaped like `.scratch/bureport.md`; assert row count, surviving text and tool call, a single non-NULL token row, field-wise max sums, a second response counted fully, unkeyed lines not merged, and `session_token_usage` after `write_session`. Run those tests and confirm they fail.
4. Write code and run green: from `_parse_messages`, pass each kept assistant line's `(message.id, requestId)` when both are non-empty strings, else `None`. The helper sets the four token fields to the field-wise max on the last message of each key group and `NULL` on the other messages in that group. `None` keys are left alone. Non-int counts are ignored for the max. Update the module docstring so identity stays per kept line and usage is once per response. Re-run the new tests, then the existing `test_ingest_claude.py` module.

### 2. Drop forked parent copies on subagents — executable

- Files: `skills/sr-search/src/stockroom/ingest/model.py`, `skills/sr-search/src/stockroom/ingest/claude.py`, `skills/sr-search/src/stockroom/ingest/__init__.py`, `skills/sr-search/tests/test_ingest_orchestrator.py`

1. Stub tests: add `test_forked_subagent_copy_does_not_add_parent_usage` to `test_ingest_orchestrator.py` with a docstring and an empty body.
2. Stub interface: add optional `api_message_id: str | None = None` and `request_id: str | None = None` on `NormalizedMessage`, documented as parse-time provenance the writer does not persist. Add `drop_copied_parent_usage(parent: NormalizedSession, subagents: list[NormalizedSession]) -> None` in `claude.py` with a docstring and an empty body.
3. Write tests and run red: under `tmp_path`, a parent `.jsonl` with one multi-block response and a `subagents/agent-*.jsonl` whose first assistant line repeats that `(message.id, requestId)` and whose next assistant line is a different response. Point `STOCKROOM_CLAUDE_ROOT` at that tree, `ingest(full=True, harness="claude")`, and assert parent `session_token_usage` is the one response, the copied subagent message has `NULL` tokens, and the subagent session totals equal only its own response. Run again and assert the same totals. Confirm the test fails.
4. Write code and run green: `_build_message` sets the two provenance fields. `_parse_discovered` calls `drop_copied_parent_usage` after the Claude parent and its subagents are parsed. The helper clears the four token fields on a subagent message whose `(api_message_id, request_id)` is in the parent's set. It does not change text, tool calls, or the parent. Re-run the new test, then `tests/test_ingest_orchestrator.py` and `tests/test_ingest_writer.py`.

### 3. Document the count and the re-ingest limit — prose/policy

- Files: `docs/architecture/warehouse.md`, `docs/user-guide/load/basic.md`
- No tests: prose/policy artifact

1. In the message-grain bullet of Dual-grain token usage, state that Claude keeps one row per content-block line and stores the four counts once per `(message.id, requestId)` (field-wise max on one row, `NULL` on the others), and that a subagent line repeating its parent's response id does not carry those counts.
2. On the ingest page, state that `stockroom ingest --full` (or `--harness claude`) is what rewrites sessions whose transcripts are still on disk after this correction, and that sessions whose transcripts are gone keep the counts already stored.


## Technology Validation

No new technology - validation not required


## Dependencies

- pytest and the in-memory `migrated_con` fixture (full migration chain, including `0007`)
- `stockroom.ingest.writer.write_session` (delete-then-insert; no column-list change)
- VIEW `session_token_usage` (unchanged `SUM`)
- Claude discovery layout already implemented in `stockroom.ingest.sources`


## Challenges & Mitigations

- A new JSONL under `tests/fixtures/transcripts/claude/` would change `expected_rows.json`: build repro files in `tmp_path` only.
- Incremental ingest keys off the parent file mtime, so old sessions stay wrong until `ingest --full`: say that on the ingest page; do not add a second rewrite path.
- Vanished transcripts cannot be recomputed, and the consecutive-triple collapse is not exact: do not ship warehouse DML for them. Migration `0007` is already structural-only.
- Attributing "the last line's usage" undercounts output when an earlier line is higher: the test where the last line is lower forces field-wise max.
- Fork clearing could wipe a subagent's own response: the test includes a second subagent line with a different id, and the helper matches only keys present on the parent.
- `api_message_id` / `request_id` are easy to mistake for warehouse columns: the writer INSERT list stays unchanged; the model docstring says they are not persisted. No migration.


## Pre-Mortem

- The plan fixes the view with a divisor or a heuristic UPDATE, and real responses that share a cache triple get merged: the plan never changes `0007` and refuses vanished-row DML. Within-session grouping uses the API identity, which the report measured as the true response key.
- The plan stores corrected tokens but the dashboard keeps reading a different sum: the dashboard already reads `session_token_usage`, and that view is the assertion in step 1. No dashboard change.
- Parent and subagent are ingested apart, so the fork clear never runs: discovery parses them together whenever the parent file exists, and the test goes through `ingest`, not a direct helper call alone. A parent file that is already gone is the vanished case and stays untouched.


## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Pre-Mortem complete
- [ ] Preflight
- [ ] Build
- [ ] QA
