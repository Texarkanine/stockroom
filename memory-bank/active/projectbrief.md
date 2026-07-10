# Project Brief

## User Story

As a stockroom operator on Linux, WSL, or macOS, I want stockroom-owned runtime data to live under the XDG Base Directory layout so that paths are predictable, consistent with *nix conventions, and overrideable via standard env vars.

## Use-Case(s)

### Use-Case 1 — Fresh install

A new install resolves warehouse DB, lock, and scheduler logs under the XDG data home: `$XDG_DATA_HOME/stockroom/` when set, else `~/.local/share/stockroom/` (single tree including logs).

### Use-Case 2 — Explicit override

Setting `STOCKROOM_HOME` continues to bypass XDG resolution entirely (tests and power users).

### Use-Case 3 — Existing private installs

Out of product scope: the two existing machines will fresh-install or manually `cp` the warehouse into the new home. No automated legacy migration.

## Requirements

1. On all Unix-like platforms (Linux, WSL, macOS), resolve stockroom paths via XDG data-home env + spec default — one layout everywhere; no macOS-native Application Support tree.
2. `STOCKROOM_HOME` remains an absolute override over XDG resolution.
3. Dependents of `home_dir()` (`warehouse_path`, `lock_path`, schedule log path) follow the new resolution.
4. `stockroom doctor` reports which home is active and how it was chosen.
5. Docs/skills / memory bank name the new default paths; reconcile stale O1 "XDG-aware" planning language.
6. Tests cover XDG env resolution and default-path fallback (including macOS-like unset-`XDG_*` environments).

## Constraints

1. Out of scope: harness ingest roots (`~/.cursor/projects`, `~/.claude/projects`).
2. Out of scope: Windows-native paths (post-v1).
3. Out of scope: replacing cron/launchd scheduler integration — only where stockroom *stores* data/logs changes.
4. Out of scope: legacy `~/.stockroom/` detection, auto-migration, conflict handling, or doctor legacy facts (operator waiver vs issue #3 migration acceptance).
5. Authoritative starting point: [GitHub issue #3](https://github.com/Texarkanine/stockroom/issues/3), amended by operator direction above.

## Acceptance Criteria

1. `home_dir()` and dependents resolve via XDG data home + spec defaults on Linux, WSL, and macOS.
2. `STOCKROOM_HOME` still overrides everything (tests unchanged or updated deliberately).
3. No migration code ships; issue #3 migration items are explicitly waived for this task.
4. Memory bank / tech context updated; stale O1 language reconciled with shipped XDG defaults.
5. Tests cover XDG env resolution and default-path fallback on macOS-like environments.
6. Doctor reports active home and home-source.
