---
task_id: semantic-cli-filters
date: 2026-10-05
complexity_level: 2
---

# Reflection: semantic-cli-filters

## Summary

`stockroom semantic` now takes optional `--harness` and `--role` and ranks inside that set. The unfiltered command still uses HNSW. QA passed with no rework.

## Requirements vs Outcome

Every requirement in the brief shipped. Unknown `--harness` exits 0. A bad `--role` exits 2. The skills teach the pronoun map and the empty-scope meaning. Project, time, model, and ordinal filters stayed out. The scoped path dedups with one `QUALIFY` statement, which is the preflight advisory, not a second messages lookup.

## Plan Accuracy

The file list and the test list held. The surprise was quantitative: 32 nearer 384-d outsiders are enough for a `WHERE` on the HNSW limit query to return no in-scope row. The plan knew a tiny fixture would hide that, and the probe confirmed the count. The local uv 0.8.22 failure of the docs lock test was not in the plan; the CI pin 0.12.22 passes it, and the lock was not rewritten.

## Build & QA Observations

The six library tests failed while the new arguments were ignored, then passed on the joined rank. QA re-ran the semantic file (33 passed, 1 torch skip) and found nothing blocking.

## Insights

### Technical

- DuckDB 1.5.4 VSS applies `WHERE` after the HNSW pick. A scope has to rank the filtered rows. `QUALIFY row_number()` is the max-sim dedup for that path, and it does not need `OVERFETCH`.

### Process

- A scope test on a handful of rows can pass the implementation we had rejected. The starvation count has to be measured against the naive query, not assumed from the small fixture.
- `make test` on this machine calls `uv` 0.8.22 for the hermetic lock check. That binary reports the revision-5 root lock as stale. uv 0.12.22, the CI pin, accepts it. Do not refresh the lock to satisfy 0.8.22.

### Million-Dollar Question

The two query shapes are the design. Unfiltered search keeps the index. A scope never shares that limit query. Building it as one function with that split is the version that falls out if the scope had been there from the start. A filter-aware index would be a different product decision, and this corpus does not need it.

# Reflection: semantic-cli-filters rework

## Summary

Review 5420273503 asked the human pages to stop listing `--harness` and `--role`. Those three listings are gone. The flags stay in `skills/sr-semantic/SKILL.md`. QA passed.

## Requirements vs Outcome

The three rework requirements shipped. The CLI Role cell is the subcommand's job again. The search page and the skill index no longer repeat the flags. The skill flag home, the `sr-search` route row, and the architecture two-path sentence stayed. No engine or test change.

## Plan Accuracy

The four steps matched the files. Step 4, the explicit leave-alone list, was the part that mattered: a duplication cleanup will also delete a router row that mentions the same flags unless the plan names it.

## Build & QA Observations

The edits were deletions. `make docs-build` passed. QA found no extra human-page listing. `test_docs_lock_is_not_stale` still fails on this machine's uv 0.8.22 and was left alone, same as the first build.

## Insights

### Technical

Nothing notable.

### Process

Name what a duplication review is allowed to keep. The route row and the two-path sentence both mention the flags, and both are supposed to.

### Million-Dollar Question

The pages that already refuse to fork skill flag tables are the design. The listings were drift. Putting the flags only in the skill is the version that falls out if that rule had been followed when the flags were added. A generator that emits the skill table from argparse is a later idea, not this fix.
