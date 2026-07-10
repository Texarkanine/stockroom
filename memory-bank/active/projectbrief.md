# Project Brief

## User Story

As a stockroom user with Cursor and/or Claude Code plugins, I want the local dashboard on port 6767 to serve from the healed engine after a plugin-root move so that one session/workspace cycle leaves both the CLI and the running dashboard current — without tearing down the dashboard when only one harness closes.

## Use-Case(s)

### Use-Case 1

Plugin updates or moves (e.g. local → marketplace cache). Session/workspace start heals the shim and env. A dashboard started from the old path still holds 6767. Next `stockroom dashboard` (from the hook) replaces that owned stale listener and binds from the new engine.

### Use-Case 2

Cursor and Claude are both open. One harness exits. The dashboard keeps running for the other. No close/stop hooks kill it.

### Use-Case 3

Something else already listens on 6767. Stockroom does not kill it; launch prints the URL and exits successfully (hook never-error).

## Requirements

1. After one hook/session cycle that heals the shim to a new engine dir, the process serving `http://127.0.0.1:6767/` must be that new engine (or equivalent identity), not a leftover from a dead plugin path.
2. Multi-harness: closing one harness must not stop the dashboard.
3. Preserve the hook contract: idempotent, fire-and-forget, never errors, never ingests/migrates.
4. Do not kill unrelated listeners on 6767.
5. Implement per the creative decision: start-time identity-aware replace in the dashboard launcher (not close hooks).

## Constraints

1. Decision authority: `memory-bank/active/creative/creative-dashboard-lifecycle-after-plugin-move.md` (Option B).
2. Dashboard remains a detached machine-scoped singleton on port 6767.
3. Replace/kill failures must degrade to current success behavior (print URL, exit 0).
4. Identity proof required before any process control (pidfile/identity under stockroom home and/or observed stockroom.dashboard match).

## Acceptance Criteria

1. With a stale owned dashboard on 6767 from old `APP_DIR`, running `stockroom dashboard` from the new engine replaces it; `ps` shows the new engine path.
2. With a matching-identity dashboard already up, launch remains an idempotent no-op (print URL, no respawn).
3. Foreign listener on 6767 is left alone; exit 0.
4. No SessionEnd / sessionEnd / stop hooks added for dashboard shutdown.
5. Unit tests cover free / same identity / stale owned / foreign decision matrix; full suite green.
