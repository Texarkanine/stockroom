# Project Brief

## User Story

As a Cursor user on macOS, I want the plugin to heal the on-path shim even when `sessionStart` fails to dispatch, and I want the dashboard to guide me correctly when it is broken after a plugin update, so that I am not stuck with a dead UI and opaque JSON errors.

## Use-Case(s)

### Use-Case 1: Session-start miss on macOS Cursor

`sessionStart` does not fire reliably on macOS Cursor, so `CURSOR_PLUGIN_ROOT` never arrives and the plugin cannot rectify the shim or launch the dashboard. `beforeSubmitPrompt` does fire reliably (but far more often). On each submit, a heavily trimmed, non-blocking shim rectify runs as suspenders while `sessionStart` remains for the full rectify + dashboard path.

### Use-Case 2: Stale dashboard after plugin update

After a plugin update, a still-bound dashboard may serve broken content. Prefer detecting whether the shim needs rectify versus whether the dashboard needs replace, and tell the user the right remedy. Never advise `stockroom dashboard --replace` when the real problem is a shim that needs rectifying. If precise detection is hard, a pretty troubleshooting page with docs links is acceptable — never bare `{"error":"not found"}` JSON for that failure surface.

## Requirements

1. Add a Cursor-only `beforeSubmitPrompt` hook that runs a heavily trimmed, non-blocking `shim rectify` (no dashboard launch on that path).
2. Keep the existing Cursor `sessionStart` hook (rectify + dashboard).
3. Do not restore or add `workspaceOpen`.
4. Prefer detecting and messaging: (a) shim needs rectify, (b) dashboard needs replace.
5. Never advise `--replace` when the shim is the real problem (shim-first diagnosis / messaging).
6. If detection is too hard, fall back to a pretty troubleshooting page on the relevant 404/failure surface with remedial commands and canonical docs links — not bare JSON.

## Constraints

1. `beforeSubmitPrompt` must not slow prompt submission — truly non-blocking fire-and-forget (Cursor can gate send on this hook; design must exit immediately).
2. Trim aggressively relative to session-start work (no dashboard; no heavy ensure-env / torch sync on the hot path unless an equally non-blocking design is proven safe).
3. Hook doctrine remains: idempotent, fault-tolerant, never errors into the harness.
4. Claude Code hooks are out of scope for the new event (Cursor-only addition).
5. SPA/data 404s (e.g. unknown session id) and unrelated query-param noops are out of scope unless they collide with the recovery surface.

## Acceptance Criteria

1. Cursor `hooks/cursor-hooks.json` registers `beforeSubmitPrompt` that attempts shim rectify without blocking submit.
2. `sessionStart` behavior is unchanged in intent (rectify + dashboard).
3. When the dashboard can detect shim-needs-rectify, it tells the user to rectify (not `--replace`).
4. When the dashboard can detect needs-replace (and shim is fine), it tells the user to run `stockroom dashboard --replace`.
5. Users never see bare `{"error":"not found"}` as the only recovery UI for the stale/broken dashboard surface — either targeted guidance or a pretty troubleshooting page with docs links.
6. Tests cover the new hook packaging contract and the recovery UX / detection behavior.
