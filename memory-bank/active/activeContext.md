# Active Context

## Current Task: exact-message-text-retrieval
**Phase:** BUILD - COMPLETE

## What Was Done
- Added `--detail raw` (unbounded, preserve whitespace) through `truncate_cell` → render → query/semantic CLIs
- Left `full` as unbounded + single-line
- Documented `--format json --detail raw` in `sr-query` / `sr-semantic` skills + system-model + systemPatterns
- `make ci` green: 510 passed, 3 skipped

## Files Modified
- `/home/mobaxterm/git/stockroom/skills/sr-search/src/stockroom/truncate.py`
- `/home/mobaxterm/git/stockroom/skills/sr-search/src/stockroom/render.py`
- `/home/mobaxterm/git/stockroom/skills/sr-search/src/stockroom/query.py`
- `/home/mobaxterm/git/stockroom/skills/sr-search/src/stockroom/semantic.py`
- `/home/mobaxterm/git/stockroom/skills/sr-search/tests/test_truncate.py`
- `/home/mobaxterm/git/stockroom/skills/sr-search/tests/test_render.py`
- `/home/mobaxterm/git/stockroom/skills/sr-search/tests/test_query_cli.py`
- `/home/mobaxterm/git/stockroom/skills/sr-search/tests/test_semantic.py`
- `/home/mobaxterm/git/stockroom/skills/sr-search/tests/test_skill_hygiene.py`
- `/home/mobaxterm/git/stockroom/skills/sr-query/SKILL.md`
- `/home/mobaxterm/git/stockroom/skills/sr-semantic/SKILL.md`
- `/home/mobaxterm/git/stockroom/skills/sr-search/references/system-model.md`
- `/home/mobaxterm/git/stockroom/memory-bank/systemPatterns.md`

## Deviations
- None — built to plan (plus B10 hygiene pin for skill docs)

## Next Step
- QA review
