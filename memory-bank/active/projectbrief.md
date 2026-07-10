# Project Brief

## User Story

As a Cursor plugin user, I want the stockroom `sessionStart` hook to actually run when I open a new Agent chat so that the local dashboard comes up automatically without manual `/sr-dashboard`.

## Use-Case(s)

### Use-Case 1

Install stockroom from the Cursor marketplace (or local plugin). Open a new Agent/Composer conversation. The plugin `sessionStart` hook fires, rectifies the shim, and launches `stockroom dashboard` so `http://127.0.0.1:6767/` is reachable.

### Use-Case 2

On both WSL2 (Cursor via WSL) and native macOS, the same Cursor-native hook schema and command shape work — no harness-specific PATH-only workaround that leaves the schema wrong.

## Requirements

1. Restructure `hooks/cursor-hooks.json` to the documented Cursor native hooks schema (flat `sessionStart` entries with top-level `command`), per [Cursor Hooks](https://cursor.com/docs/hooks).
2. Harden the Cursor hook command: explicit `PATH` including `$HOME/.local/bin`, drain stdin JSON, timeout in seconds.
3. Update packaging contract tests that currently encode the Claude-shaped Cursor hook layout.
4. Leave `hooks/claude-hooks.json` unchanged (works today).

## Constraints

1. Do not modify Claude Code hooks or their tests beyond what is required to keep shared helpers accurate.
2. Prefer clean-break schema fix over backwards-compatible dual-format support.
3. Follow TDD for all code/config contract changes.

## Rework

### Additional requirements (2026-07-10)

1. Cursor hook event: `workspaceOpen` (not `sessionStart`) — [Cursor Hooks](https://cursor.com/docs/hooks#workspaceopen).
2. Document **Include third-party Plugins, Skills, and other configs** until [plugin hooks not loading](https://forum.cursor.com/t/plugin-hooks-not-loading-into-cursor-ide/156702) is fixed; include `docs/img/3rd-party-configs.png`.
3. Keep filename `hooks/cursor-hooks.json` (no rename).
4. Leave Cursor hook stderr visible (stdout may stay quiet).
5. Minimal diff — Claude hooks untouched; no drive-by renames.

