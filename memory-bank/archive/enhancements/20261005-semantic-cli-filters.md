---
task_id: semantic-cli-filters
complexity_level: 2
date: 2026-10-05
status: completed
---

# TASK ARCHIVE: semantic-cli-filters

## SUMMARY

`stockroom semantic` now takes optional `--harness` and `--role` and ranks inside that set. The unfiltered command still uses HNSW. A review then removed the flag listings from the human pages. The flag home is `skills/sr-semantic/SKILL.md`. QA passed both times.

## REQUIREMENTS

- Optional `--harness` and `--role`. Omitting a flag leaves that dimension open. The two flags combine with AND.
- `--role` accepts only `user` and `assistant` and exits 2 otherwise. `--harness` is one free exact string. An unknown value is an empty result and exits 0. Repeating a flag is not OR.
- A scope ranks the joined set before the cut to `-k`. It is not a `WHERE` on the HNSW `ORDER BY distance LIMIT` query. A nearer outsider must not hide an insider.
- With neither flag set, ranking stays on HNSW.
- `sr-semantic` teaches the pronoun map. Ids, counts, dates, and projects stay `sr-query`. `sr-search` may pass the flags when the question names a speaker or a harness.
- No project, time, model, or ordinal filter. No new index. Unfiltered search can still be dominated by a repeated opening turn.
- Review 5420273503: human pages stop listing the flags. The CLI Role cell is the subcommand's job. The `sr-search` route row and the architecture two-path sentence stay.

## IMPLEMENTATION

`run_semantic_search` takes optional `harness` and `role`. Neither flag set keeps the HNSW path. Either flag set ranks `embeddings` joined to `messages` under those equalities, then max-sim dedup with one `QUALIFY row_number()` and a cut to `-k`. `OVERFETCH` is not used on that path. The predicate is not added to the HNSW limit query. DuckDB 1.5.4 VSS post-filters that shape and can return no rows.

`skills/sr-semantic/SKILL.md` holds the pronoun map, the accepted values, and the empty-result meaning. `skills/sr-search/SKILL.md` keeps the route row that decides when to pass the flags. `docs/architecture/embeddings.md` and `memory-bank/systemPatterns.md` keep the two-path sentence.

The first build also mentioned the flags on `docs/advanced/cli.md`, `docs/user-guide/search.md`, and `docs/user-guide/skills.md`. The rework removed those listings. The CLI Role cell is `Vector (semantic) search.` The skill index still says the command is not for id lookups, counts, dates, or projects.

## TESTING

`skills/sr-search/tests/test_semantic.py` covers harness scope, role scope, AND, unknown harness, the limit after the scope, a 32-outsider starvation case, and the CLI exits. The new tests failed while the arguments were ignored, then passed on the joined rank.

`make lint` passed. The first `make test` was 880 passed, 4 skipped, plus 134 dashboard JS tests. `/niko-qa` re-ran the semantic file: 33 passed, 1 torch skip. The rework was prose. `make docs-build` passed. Pytest was 881 passed, 4 skipped, 1 failed: `test_docs_lock_is_not_stale` on this machine's uv 0.8.22. uv 0.12.22, the CI pin, accepts the lock. The lock was not rewritten. Rework QA passed with no engine or test change.

## LESSONS LEARNED

DuckDB 1.5.4 VSS applies `WHERE` after the HNSW pick. A scope has to rank the filtered rows. `QUALIFY row_number()` is the max-sim dedup for that path.

A scope test on a handful of rows can pass the implementation that was rejected. Thirty-two nearer 384-d outsiders are enough for the post-filtered limit query to miss the in-scope row. The count has to be measured against the naive query.

A duplication cleanup will also delete a router row that mentions the same flags, unless the plan names what stays. The route row and the two-path sentence are allowed to name the flags. The human pages are not.

## PROCESS IMPROVEMENTS

Name the leave-alone list in a duplication review before editing. The flag home, the router, and the architecture sentence are three different jobs.

Do not refresh the root `uv.lock` to satisfy uv 0.8.22. CI pins uv 0.12.22, and that binary accepts the committed revision.

## TECHNICAL IMPROVEMENTS

The two query shapes are the design. Unfiltered search keeps the index. A scope never shares that limit query. A filter-aware index would be a different product, and this corpus does not need it.

Generating the skill's flag line from the `argparse` definitions, the way the warehouse diagram is generated from migration comments, would stop the same fact landing on four pages. That is a later idea. This fix puts the flags only in the skill.

## NEXT STEPS

Pull request: https://github.com/Texarkanine/stockroom/pull/136
