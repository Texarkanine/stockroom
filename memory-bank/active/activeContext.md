# Active Context

## Current Task: fix-cursor-sessionstart-hook-schema
**Phase:** BUILD - IN-PROGRESS

## What Was Done
- Clarified intent for [#12](https://github.com/Texarkanine/stockroom/issues/12): Cursor `sessionStart` never fires; Claude third-party hook does; root cause is wrong hooks.json schema (Claude nested shape + `version: 1`), not PATH-only.
- Operator confirmed: leave Claude hooks alone.
- Classified as Level 1 (quick bug fix — single component: Cursor hook config + its packaging contract tests).

## Next Step
- TDD: update packaging tests for Cursor flat schema, then fix `hooks/cursor-hooks.json`.
