# Project Brief

## User Story

As a Cursor user on macOS, I want the plugin to heal the on-path shim even when `sessionStart` fails to dispatch, and I want the dashboard to show a clear diagnostic page when it cannot load, so that I am not stuck with a dead UI and opaque JSON errors.

## Use-Case(s)

### Use-Case 1: Session-start miss on macOS Cursor

`sessionStart` does not fire reliably on macOS Cursor, so `CURSOR_PLUGIN_ROOT` never arrives and the plugin cannot rectify the shim or launch the dashboard. `beforeSubmitPrompt` does fire reliably (but far more often). On each submit, a heavily trimmed, non-blocking **path-only** shim rectify runs as suspenders while `sessionStart` remains for the full rectify + dashboard path.

### Use-Case 2: Broken / stale dashboard UI

After a plugin update (or similar), a still-bound dashboard may be unable to serve real UI. MVP: recognize that failure and serve **one** pretty diagnostic HTML page with shim-first ordered remedies and links to the online user manual — never bare `{"error":"not found"}` JSON for that surface. Exact root-cause classification is out of scope for this task.

## Requirements

1. Add a Cursor-only `beforeSubmitPrompt` hook that runs a heavily trimmed, non-blocking path-only `shim rectify` (no dashboard launch; no ensure-env on that path).
2. Keep the existing Cursor `sessionStart` hook (full rectify + dashboard).
3. Do not restore or add `workspaceOpen`.
4. When the dashboard cannot serve real static/UI content, return one in-memory diagnostic HTML page (ordered remedies + online docs links).
5. Diagnostic copy must be shim-first: never present `--replace` as the sole or leading remedy.
6. API/session JSON 404 contracts stay unchanged.

## Constraints

1. `beforeSubmitPrompt` must not slow prompt submission — truly non-blocking (Cursor can gate send on this hook; design must exit immediately).
2. Trim aggressively: path-only rectify on the hot path; env heal stays on sessionStart / explicit ensure-env / `sr-initialize`.
3. Hook doctrine remains: idempotent, fault-tolerant, never errors into the harness.
4. Claude Code hooks are out of scope for the new event (Cursor-only addition).
5. SPA/data 404s (e.g. unknown session id) and unrelated query-param noops are out of scope.
6. No shim-vs-replace classifier in MVP (deferred).

## Acceptance Criteria

1. Cursor `hooks/cursor-hooks.json` registers `beforeSubmitPrompt` that attempts path-only shim rectify without blocking submit.
2. `sessionStart` behavior is unchanged in intent (full rectify + dashboard).
3. Static/document misses (including broken listener with missing `index.html`) return diagnostic HTML, not bare JSON.
4. Diagnostic page includes ordered remedies (shim/session → ensure-env/`sr-initialize` → `--replace`) and links to online troubleshooting docs.
5. API unknown-route and missing-session responses remain JSON 404.
6. Tests cover the new hook packaging contract and the diagnostic page HTTP/HTML behavior.
