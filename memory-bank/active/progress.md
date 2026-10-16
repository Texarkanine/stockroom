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

## 2026-10-16 - PLAN - COMPLETE

* Work completed
    - Probed Claude Code 2.1.301 headless with a throwaway plugin and a project skill. In plugin skills, only the exact tokens `${CLAUDE_PLUGIN_ROOT}` and `${CLAUDE_SKILL_DIR}` are substituted; in project skills, only `${CLAUDE_SKILL_DIR}`.
    - Gathered Cursor evidence: staff endorse `${CURSOR_PLUGIN_ROOT}` in hooks; the variable is undocumented for agent shells and skill text.
    - Checked real install dirs: both harness caches contain `.git` and `Makefile`.
    - Audited both hook files (`claude plugin validate .` passes) and the docs.
    - Wrote the L2 plan to `tasks.md`: a 5-rule Step 2 resolution, a guarded Step 7 install, two doc fixes, and a new `test_initialize_context.py` that runs the Step 2 block under modeled harness rendering.
* Decisions made
    - Take `APP_DIR` from this skill's sibling directory, never from a plugin-root variable. Plugin-root signals pick only `OWNER`.
    - Owner order: no engine → none; `${CURSOR_PLUGIN_ROOT}` → cursor; `${CLAUDE_PLUGIN_ROOT}` (substituted) → claude; `*/.cursor/plugins/*` or `*/.claude/plugins/*` path → that harness; otherwise dev.
    - Hooks unchanged: they already receive the root by the documented mechanism.
    - `claude --plugin-dir <checkout>` resolves to `claude`, matching that session's own SessionStart hook.
* Insights
    - "Makefile plus .git means dev", the bug report's option 3, would misfire: marketplace installs are git clones that include the Makefile.
    - The bug has existed since plugin 0.1.1. Agents improvised silently, which is why nobody noticed.
