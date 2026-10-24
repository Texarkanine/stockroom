# Active Context

## Current Task: warehouse-file-growth, milestone 7 (session-start launch)
**Phase:** BUILD - COMPLETE

## What Was Done
- `launch` spawns `python -m stockroom.check --foreground` in a new session with discarded standard streams, and returns without waiting
- Only the child calls `entry`. An omitted home is `resolve_home()`'s path, not the `(path, source)` tuple
- Both session-start hooks run that module after `stockroom dashboard`. `beforeSubmitPrompt` does not
- `stockroom check` stays an unknown command
- The user-guide and architecture hook descriptions say session start rehearses, then later replaces the warehouse and keeps the original

## Files
- `/home/mobaxterm/git/stockroom/skills/sr-search/src/stockroom/check.py`
- `/home/mobaxterm/git/stockroom/skills/sr-search/tests/test_check.py`
- `/home/mobaxterm/git/stockroom/skills/sr-search/tests/test_dispatcher_cli.py`
- `/home/mobaxterm/git/stockroom/skills/sr-search/tests/test_packaging.py`
- `/home/mobaxterm/git/stockroom/hooks/claude-hooks.json`
- `/home/mobaxterm/git/stockroom/hooks/cursor-hooks.json`
- `/home/mobaxterm/git/stockroom/docs/user-guide/troubleshooting/index.md`
- `/home/mobaxterm/git/stockroom/docs/user-guide/quickstart.md`
- `/home/mobaxterm/git/stockroom/docs/user-guide/dashboard.md`
- `/home/mobaxterm/git/stockroom/docs/user-guide/load/schedule.md`
- `/home/mobaxterm/git/stockroom/docs/user-guide/installed-layout.md`
- `/home/mobaxterm/git/stockroom/docs/architecture/lifecycle.md`
- `/home/mobaxterm/git/stockroom/docs/architecture/index.md`
- `/home/mobaxterm/git/stockroom/memory-bank/systemPatterns.md`

## Next Step
- QA review
