# Project Brief

## User Story

As a stockroom operator on Linux, WSL, or macOS, I want stockroom-owned runtime data to live under the XDG Base Directory layout so that paths are predictable, consistent with *nix conventions, and overrideable via standard env vars — without losing existing `~/.stockroom/` data.

## Use-Case(s)

### Use-Case 1 — Fresh install

A new install resolves warehouse DB, lock, and scheduler logs via `XDG_*` env vars when set, else the Freedesktop default paths (`~/.local/share/stockroom/`, `~/.local/state/stockroom/`, etc.).

### Use-Case 2 — Existing install

An operator with legacy `~/.stockroom/warehouse.duckdb` runs stockroom and gets a one-time, idempotent migration (or clear doctor guidance) into the XDG layout, with no silent data loss when both locations have divergent content.

### Use-Case 3 — Explicit override

Setting `STOCKROOM_HOME` continues to bypass XDG resolution entirely (tests and power users).

## Requirements

1. On all Unix-like platforms (Linux, WSL, macOS), resolve stockroom data/state paths via XDG env vars + spec defaults — one layout everywhere; no macOS-native `~/Library/Application Support/` tree.
2. `STOCKROOM_HOME` remains an absolute override over XDG resolution.
3. Dependents of `home_dir()` (`warehouse_path`, `lock_path`, schedule log path) follow the new resolution.
4. Legacy `~/.stockroom/` migration is implemented (or explicitly deferred with rationale documented on the issue) with safe conflict handling.
5. `stockroom doctor` (or similar) reports which home is active and whether legacy data was found.
6. Docs/skills (`sr-initialize`, system-model / memory bank) name the new default paths; reconcile stale O1 "XDG-aware" planning language.
7. Tests cover XDG env resolution, default-path fallback (including macOS-like unset-`XDG_*` environments), and legacy-home detection/migration.

## Constraints

1. Out of scope: harness ingest roots (`~/.cursor/projects`, `~/.claude/projects`).
2. Out of scope: Windows-native paths (post-v1).
3. Out of scope: replacing cron/launchd scheduler integration — only where stockroom *stores* data/logs changes.
4. Scope is directory layout + env-var resolution, not platform scheduler rewrites.
5. Authoritative spec: [GitHub issue #3](https://github.com/Texarkanine/stockroom/issues/3).

## Acceptance Criteria

1. `home_dir()` and dependents resolve via XDG env vars + spec defaults on Linux, WSL, and macOS.
2. `STOCKROOM_HOME` still overrides everything (tests unchanged or updated deliberately).
3. Legacy `~/.stockroom/` migration path documented and implemented (or explicitly deferred with rationale on the issue).
4. Memory bank / tech context updated; stale O1 "XDG-aware" planning language reconciled with shipped behavior.
5. Tests cover XDG env resolution, default-path fallback on macOS-like environments, and legacy-home detection/migration.
