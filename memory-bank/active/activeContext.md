# Active Context

## Current Task: query-cookbook
**Phase:** BUILD - COMPLETE

## What Was Done
- TDD: `skills/sr-search/tests/test_query_cookbook.py` (path/wiring + Claude builtin denylist sync)
- Cookbook SSOT under `skills/sr-query/references/cookbook/` (index, token-usage, tools, skills-claude, skills-cursor)
- Agent discoverability: `sr-query/SKILL.md` Cookbook section + pointers; `sr-search` routing row for full skills/tools tables
- Human docs: `docs/advanced/cookbook.md` snippet includes, nav, advanced index mention, user-guide pointer
- `properdocs.yaml` snippet comment; `systemPatterns.md` docs-ownership cookbook sentence
- Verification: cookbook tests green; `make test` 626 passed / 4 skipped + 92 JS; `make docs-build` strict green; warehouse smoke OK

## Deviations
- Removed markdown peer-links between skill recipes (dual-audience: relative links broke strict docs build when snippet-included under `docs/advanced/`)

## Next Step
- QA phase (`niko-qa`) after phase-transition commit
