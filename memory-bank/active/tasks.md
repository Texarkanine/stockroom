# Task: semantic-cli-filters

* Task ID: semantic-cli-filters
* Complexity: Level 2
* Type: simple enhancement

Add optional `--harness` and `--role` to `stockroom semantic`. When either is set, rank the joined filtered owner set and then max-sim dedup and cut to `-k`. When neither is set, keep the current HNSW path. Teach `sr-semantic` and `sr-search` the pronoun map. Do not add project, time, model, or ordinal filters.

## Test Plan (TDD)

### Behaviors to Verify

- Harness scope: a distance-0 message in another harness plus a different-text message in the requested harness → only the in-scope message is returned
- Role scope: a distance-0 message of the other role plus a different-text message of the requested role → only the in-scope message is returned
- AND: a harness-only match and a role-only match, both distance 0 to the query, plus one message that matches both → only the both-match is returned
- Unknown harness: `harness="nosuch"` → `[]`
- Limit after scope: more in-scope messages than `limit`, plus nearer out-of-scope messages → length is `limit` and every hit matches the scope
- Index starvation: enough nearer out-of-scope chunks that a post-filtered HNSW `LIMIT` returns none of the in-scope row → the in-scope message is still returned
- Unfiltered regression: existing `test_semantic.py` cases stay green with the new default arguments
- CLI `--role user`: output contains the user hit and not the distance-0 assistant outsider
- CLI `--harness`: output contains only that harness
- CLI bad `--role`: `SystemExit` code 2, encoder factory not called
- CLI unknown `--harness`: exit 0 and the empty tsv shape (header, no data row)
- CLI repeated `--harness`: last value only, not the union of both

### Test Infrastructure

- Framework: pytest, configured in `skills/sr-search/pyproject.toml`, run via `make test` or `uv --directory skills/sr-search --no-config run --no-sync pytest`
- Test location: `skills/sr-search/tests/test_semantic.py`
- Conventions: torch-free `FakeEncoder` and `migrated_con` / `warehouse_home`; CLI tests call `semantic.main(..., encoder_factory=FakeEncoder)`; docstrings state the behavior
- New test files: none

## Implementation Plan

### 1. Scoped ranking — executable

- Files: `skills/sr-search/src/stockroom/semantic.py`, `skills/sr-search/tests/test_semantic.py`

1. Stub tests: add empty cases in `test_semantic.py` for the six library behaviors above.
2. Stub interface: add `harness: str | None = None` and `role: str | None = None` to `run_semantic_search`, documented, with no filtering yet.
3. Write tests and run red: fill the assertions. The small scope tests use `FakeEncoder` with `query_prefix=""` so identical text is distance 0. The starvation test uses a fixed query vector and directly inserted `embeddings` rows, with enough nearer outsiders that the naive `WHERE` on the HNSW limit query returns no in-scope row. Run those tests and confirm they fail.
4. Write code and run green: when both scopes are absent, keep the current HNSW query. When either is set, rank `embeddings` joined to `messages` under the equalities, then the existing max-sim dedup and cut to `limit`. Do not add the predicate to the HNSW `ORDER BY distance LIMIT` query. Re-run the new tests, then the semantic file.

### 2. CLI flags — executable

- Files: `skills/sr-search/src/stockroom/semantic.py`, `skills/sr-search/tests/test_semantic.py`

1. Stub tests: empty CLI cases for `--role`, `--harness`, bad `--role`, unknown `--harness`, and repeated `--harness`.
2. Stub interface: `--harness` and `--role` on `_build_parser`. `--role` choices are `user` and `assistant`. `--harness` is one string.
3. Write tests and run red: assert the five CLI behaviors. Bad `--role` follows `test_cli_invalid_format_rejected` (`SystemExit` 2, encoder not built).
4. Write code and run green: `main` passes the parsed values into `run_semantic_search`. Repeated flags keep argparse's last value. Re-run the semantic file.

### 3. Skill guidance — prose/policy

- Files: `skills/sr-semantic/SKILL.md`, `skills/sr-search/SKILL.md`
- No tests: prose/policy artifact

1. In `sr-semantic`, replace the blanket "filters belong to `sr-query`" line. Meaning plus `--harness` and `--role` is this skill. Ids, counts, dates, and projects stay `sr-query`. Map "where I talked" to `--role user`, "where you talked" to `--role assistant`, and "where we talked" to neither flag. Say an empty scoped result means nothing in that scope matched, and that dropping the flag is the next try.
2. In `sr-search`, add a route row: a meaning question that names a speaker or a harness goes to `sr-semantic` with those flags. Counts, dates, and projects still go to `sr-query`.

### 4. Human docs and the system note — prose/policy

- Files: `docs/user-guide/search.md`, `docs/user-guide/skills.md`, `docs/advanced/cli.md`, `docs/architecture/embeddings.md`, `memory-bank/systemPatterns.md`
- No tests: prose/policy artifact

1. Add one short scope sentence to the `sr-semantic` sections of `docs/user-guide/search.md` and `docs/user-guide/skills.md`. Do not copy the skill's flag table.
2. In `docs/advanced/cli.md`, mention `--harness` and `--role` on `semantic` and point at the skill for the pronoun map. Do not add a second flag table.
3. In `docs/architecture/embeddings.md` and `memory-bank/systemPatterns.md`, record that unfiltered search stays HNSW over-fetch, and a harness or role scope ranks the joined filtered set instead. One sentence each. Leave `productContext.md` and `techContext.md` alone.

## Technology Validation

No new technology - validation not required

## Dependencies

- Existing DuckDB VSS HNSW index from migration `0003`
- `stockroom.render` for unchanged output shapes
- The design in `memory-bank/active/creative/creative-semantic-cli-filters.md`

## Challenges & Mitigations

- A small fixture will not catch HNSW post-filter starvation: the naive `WHERE` can still return the in-scope row when the index scan covers the whole tiny table. The starvation test inserts enough nearer outsiders to make that naive query return none, and asserts the in-scope row comes back.
- That starvation test can be slow. Calibrate the outsider count on the red run; do not copy 2000 rows into every other test.
- Pre-commit `make format` runs an exact `uv sync --frozen` and strips the out-of-lock torch. Library and CLI tests use `FakeEncoder`. Do not require torch for this work.
- `test_skill_hygiene.py` forbids invocation-plumbing tokens in wrapper skills. Skill edits must keep calling `stockroom semantic`, not `python -m`.

## Pre-Mortem

- The plan ships a print-time filter and the starvation test was never made large enough to fail it. The starvation test is its own behavior, and the red run has to show the naive query returning no in-scope row before the join path is accepted.
- Docs and skills keep the old "all filters are `sr-query`" line, so agents never pass the flags. Steps 3 and 4 are in the plan for that reason.
- A major version bump lands on main and conflicts with this branch. The bump is orthogonal; resolve it as a merge when it exists, and do not fold release-note work into this change.

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Pre-Mortem complete
- [x] Preflight
- [ ] Build
- [ ] QA
