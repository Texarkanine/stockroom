# Progress

Reassess how each harness exposes its plugin root (`CLAUDE_PLUGIN_ROOT`, `CURSOR_PLUGIN_ROOT`) to hooks, skill content and agent-run shell commands. Then fix `sr-initialize` context detection and engine-dir resolution, audit both hook files, correct docs that state the wrong model, and pin the detection contract with tests.

**Complexity:** Level 2

## 2026-10-16 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - Read the bug report at `.scratch/stockroom-bug-claude-plugin-root-unset.md`, plus the `sr-initialize` skill, both hook files and the related tests.
    - Confirmed in the Claude Code docs, and reproduced on 2.1.301, that `CLAUDE_PLUGIN_ROOT` is absent from the Bash tool environment.
* Decisions made
    - Level 2: a bug fix across the skill, tests, docs and possibly hooks, with no architectural change.
* Insights
    - The Claude hook is likely correct: hook commands get both inline substitution and the exported variable. The skill is the broken surface.
    - Cursor documents `${CURSOR_PLUGIN_ROOT}` expansion only for MCP config. Hook and skill behavior there is undocumented.
