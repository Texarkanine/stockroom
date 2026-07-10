# Current Task: fix-cursor-sessionstart-hook-schema

**Complexity:** Level 1

## Fix

**What broke:** Cursor plugin `sessionStart` never fired (WSL and macOS). Hook appeared in plugin customizations and on disk, but Hooks output showed no execution.

**Why:** `hooks/cursor-hooks.json` used Claude Code's nested schema (`matcher` / `hooks[]` / `type: "command"`) with only `version: 1` and camelCase `sessionStart` added. Cursor native hooks require a flat `{ "command": "..." }` entry per [Cursor Hooks](https://cursor.com/docs/hooks). Claude third-party hooks work because Cursor maps that nested format separately.

**What changed:**
- Restructured Cursor hook to flat native schema
- Hardened command: drain stdin JSON (`cat >/dev/null`), explicit `PATH` with `$HOME/.local/bin`, timeout `10` seconds (was wrongly `10000`)
- Updated packaging contract tests; left Claude hooks untouched

**Files affected:**
- `hooks/cursor-hooks.json`
- `skills/sr-search/tests/test_packaging.py`

## QA

✅ PASS — schema matches Cursor docs; command hardening present; Claude untouched; suite green. No semantic issues found.
