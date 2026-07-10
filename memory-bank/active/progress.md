# Progress

Fix Cursor plugin `sessionStart` so it loads and runs: restructure `hooks/cursor-hooks.json` to Cursor's native flat schema, harden the command (PATH, stdin drain, timeout seconds), and update packaging contract tests. Leave Claude hooks untouched.

**Complexity:** Level 1

## 2026-07-10 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - Intent clarified against [#12](https://github.com/Texarkanine/stockroom/issues/12) and [Cursor Hooks docs](https://cursor.com/docs/hooks)
    - Determined Level 1: isolated schema/command fix in Cursor hook config + packaging tests
* Decisions made
    - Leave `hooks/claude-hooks.json` unchanged
    - Treat wrong Cursor schema (Claude nested layout) as primary root cause; PATH hardening is secondary defense-in-depth
* Insights
    - Working claude-warehouse hook fires via Cursor third-party Claude mapping; native plugin hooks need Cursor flat format
    - Cursor `timeout` is in seconds; current `10000` is wrong-scale
