# Project Brief

## User Story

As a stockroom user on Mac Cursor 3.10.x, I want the plugin auto-heal/dashboard hook to fire on session start and run under a Python that satisfies `requires-python >=3.11`, so that rectify + dashboard work without relying on `workspaceOpen` or Xcode’s system Python 3.9.

## Use-Case(s)

### Use-Case 1

Open a new Cursor Agent/Composer session on Mac. The Cursor plugin hook fires (`sessionStart`), rectifies the shim/env, and launches (or refreshes) the dashboard — without the operator manually editing hook JSON.

### Use-Case 2

The hook subprocess PATH prefers `/usr/bin` / Xcode CLT `python3` (3.9) over the user’s interactive-shell 3.11. Bootstrap still selects an interpreter that can import stockroom source (`list[str] | None` and friends) and that matches the project’s `>=3.11` pin.

### Use-Case 3

Claude Code’s SessionStart hook shares the same bare-`python3` bootstrap risk; it gets the same interpreter-selection fix without regressing the empty-`.venv` / `uv run --no-sync` footgun.

## Requirements

1. Move the Cursor auto-rectify/dashboard hook from `workspaceOpen` back to `sessionStart` (operator-confirmed: `workspaceOpen` does not fire on Mac Cursor 3.10.x; `sessionStart` does).
2. Fix hook bootstrap so rectify does not run under a too-old system `python3` (observed: Xcode Python 3.9 → `TypeError` on `list[str] | None`).
3. Use uv to **select** a suitable interpreter for bootstrap; do **not** reintroduce `uv run --no-sync` for rectify (creates empty `.venv` before ensure).
4. Preserve the hook contract: idempotent, fire-and-forget, never errors; Cursor stderr remains visible for Hooks-channel diagnosis; PATH includes `~/.local/bin`.
5. Update packaging tests and docs that assert `workspaceOpen` / bare `python3` bootstrap shape.

## Constraints

1. Project pin remains `requires-python = ">=3.11"`; bootstrap must honor that, not merely “whatever `python3` is.”
2. Do not use `uv run --no-sync` for the rectify half of the hook command.
3. After rectify, dashboard launch stays on-path `stockroom dashboard` (shim → uv engine path).
4. Prior heal-after-move and dashboard-lifecycle contracts remain intact.

## Acceptance Criteria

1. `hooks/cursor-hooks.json` uses `sessionStart` (not `workspaceOpen`) with the combined rectify → dashboard command.
2. Hook bootstrap selects a `>=3.11` interpreter via uv (or equivalent uv-mediated selection), not bare unqualified `python3` that can resolve to 3.9.
3. Packaging tests encode the new event name and bootstrap contract; full suite green.
4. Docs that name `workspaceOpen` as the Cursor auto-launch event are updated to `sessionStart`.
