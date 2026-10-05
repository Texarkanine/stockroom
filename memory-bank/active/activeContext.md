# Active Context

## Current Task: semantic-cli-filters
**Phase:** QA - COMPLETE (PASS)

## What Was Done
- `run_semantic_search` takes optional `harness` and `role`. No scope keeps the HNSW path. A scope ranks the joined set in one statement, with max-sim dedup via `QUALIFY`, then cuts to `-k`.
- The CLI accepts `--harness` and `--role`. Bad `--role` exits 2. Unknown `--harness` exits 0 with an empty tsv.
- `sr-semantic` and `sr-search` teach the pronoun map. Human docs and `systemPatterns.md` record the two paths.
- Semantic tests: 33 passed, 1 skipped (torch). Full `make test`: 880 passed, 4 skipped, dashboard JS 134 passed. `tests/test_docs_lock_hermetic.py` failed under PATH uv 0.8.22 and passed under the CI pin uv 0.12.22. Lint passed.

## Key decisions
- Adopted the preflight advisory: scoped dedup is one SQL statement, not a second messages lookup and not `OVERFETCH`.
- Did not refresh `uv.lock`. The stale-lock failure is the local uv 0.8.22 against a revision-5 lock.

## Files
- `/home/mobaxterm/git/stockroom/skills/sr-search/src/stockroom/semantic.py`
- `/home/mobaxterm/git/stockroom/skills/sr-search/tests/test_semantic.py`
- `/home/mobaxterm/git/stockroom/skills/sr-semantic/SKILL.md`
- `/home/mobaxterm/git/stockroom/skills/sr-search/SKILL.md`
- `/home/mobaxterm/git/stockroom/docs/user-guide/search.md`
- `/home/mobaxterm/git/stockroom/docs/user-guide/skills.md`
- `/home/mobaxterm/git/stockroom/docs/advanced/cli.md`
- `/home/mobaxterm/git/stockroom/docs/architecture/embeddings.md`
- `/home/mobaxterm/git/stockroom/memory-bank/systemPatterns.md`

## Next Step
- QA review
