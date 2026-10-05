# Active Context

## Current Task: semantic-cli-filters
**Phase:** BUILD - COMPLETE

## What Was Done
- Removed the scoped `semantic` example and restored the CLI Role cell to `Vector (semantic) search.`
- Removed the `--harness` / `--role` sentence from the search page
- Removed the scope clause from the skill-index blurb and kept the id / count / date / project boundary
- Left `skills/sr-semantic/SKILL.md`, the `sr-search` route row, and the architecture two-path sentence unchanged

## Key Decisions
- No engine or test change. These are prose edits
- Did not refresh `uv.lock`. This machine's uv 0.8.22 fails the hermetic root-lock check that uv 0.12.22 passes

## Deviations
- None in the doc edits

## Files Modified
- `/home/mobaxterm/git/stockroom/docs/advanced/cli.md`
- `/home/mobaxterm/git/stockroom/docs/user-guide/search.md`
- `/home/mobaxterm/git/stockroom/docs/user-guide/skills.md`

## Next Step
- QA review
