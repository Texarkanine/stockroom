# Active Context

## Current Task: semantic-lookup-ids
**Phase:** PLAN - COMPLETE

## What Was Done
- Classified as Level 2 and confirmed the output-contract change.
- Planned a test-first change to `stockroom.render` so `tsv` and `table` print `session_id` and `message_id` in the same order JSON already uses (`harness`, then the two ids, then `role`, then the preview). Default stays `tsv`. JSON payload is unchanged.
- Planned prose updates to `skills/sr-semantic/SKILL.md` and the foreign-key tip in `docs/advanced/cli.md` so neither still says a second `--format json` run is required to obtain the ids.

## Next Step
- Preflight validation.
