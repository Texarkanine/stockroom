# Active Context

## Current Task: add-ingest-embed-progress-logging
**Phase:** BUILD - COMPLETE

## What Was Done
- Added optional `on_progress` to ingest orchestrator and `embed_pending`
- Wired `--verbose` on both CLIs with `print(..., flush=True)`
- Extended orchestrator, ingest CLI, and embed tests; docs mention `--verbose`
- Verification: ruff clean; 475 passed, 3 skipped

## Files Modified
- `/home/mobaxterm/git/stockroom/skills/sr-search/src/stockroom/ingest/__init__.py`
- `/home/mobaxterm/git/stockroom/skills/sr-search/src/stockroom/ingest/__main__.py`
- `/home/mobaxterm/git/stockroom/skills/sr-search/src/stockroom/embed.py`
- `/home/mobaxterm/git/stockroom/skills/sr-search/tests/test_ingest_orchestrator.py`
- `/home/mobaxterm/git/stockroom/skills/sr-search/tests/test_ingest_cli.py`
- `/home/mobaxterm/git/stockroom/skills/sr-search/tests/test_embed.py`
- `/home/mobaxterm/git/stockroom/docs/development.md`

## Key Decisions
- Progress denominator: selected conversations (ingest) / selected messages (embed)
- No elapsed-time summary enhancement (nice-to-have deferred)

## Deviations
- None — built to plan

## Next Step
- QA review (automatic per L2 workflow)
