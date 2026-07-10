# Current Task: fix-cursor-sessionstart-hook-schema

**Complexity:** Level 1

## Fix

**What broke:** Cursor plugin auto-dashboard never fired (wrong Claude-shaped schema; then plugin hooks need third-party toggle).

**Rework:** Switch Cursor event to `workspaceOpen`; keep `hooks/cursor-hooks.json`; leave stderr visible; document third-party setting + screenshot; Claude untouched.

**Files affected:**
- `hooks/cursor-hooks.json`
- `skills/sr-search/tests/test_packaging.py`
- `docs/using.md`, `docs/img/3rd-party-configs.png`
- `memory-bank/systemPatterns.md`
