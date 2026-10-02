# Active Context

## Current Task: semantic-lookup-ids
**Phase:** QA - COMPLETE (PASS)

## What Was Done
- `tsv` and `table` now print `session_id` and `message_id` after `harness` and before `role`. JSON already did. Default stays `tsv`.
- `sr-semantic` and the CLI page no longer say a second `--format json` run is required to obtain those ids. Truncation advice is unchanged.
- Preflight advisory (a neighboring-turn SQL recipe) was not added. It was advisory and outside the brief.

## Files
- `/home/mobaxterm/git/stockroom/skills/sr-search/src/stockroom/render.py`
- `/home/mobaxterm/git/stockroom/skills/sr-search/tests/test_render.py`
- `/home/mobaxterm/git/stockroom/skills/sr-search/tests/test_semantic.py`
- `/home/mobaxterm/git/stockroom/skills/sr-semantic/SKILL.md`
- `/home/mobaxterm/git/stockroom/docs/advanced/cli.md`

## Next Step
- QA passed. Proceed to `/niko-reflect`.
