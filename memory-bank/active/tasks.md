# Task: xdg-base-directory-layout

* Task ID: xdg-base-directory-layout
* Complexity: Level 3
* Type: feature

Adopt XDG Base Directory layout for stockroom-owned runtime data on all Unix-like platforms, per [issue #3](https://github.com/Texarkanine/stockroom/issues/3).

## Open Questions

### Q1: Directory layout shape (single tree vs split data/state)

**Problem:** Issue #3 proposes data under `$XDG_DATA_HOME/stockroom/` and leaves state/logs as either `$XDG_STATE_HOME/stockroom/` **or** under the same data home if we keep a single tree. Today warehouse DB, lock, and `logs/nightly.log` all live under one `home_dir()`.

**Why ambiguous:** Spec-correct split (data vs state) vs operational simplicity (one tree, `STOCKROOM_HOME` still means one root). Schedule already derives logs from `warehouse.home_dir()`; splitting changes that API surface.

**Constraints:** One layout on Linux/WSL/macOS; `STOCKROOM_HOME` overrides XDG entirely; no Windows; no Apple Application Support tree; cron/launchd mechanism unchanged (only log *path* may move).

### Q2: Legacy `~/.stockroom/` migration strategy

**Problem:** Existing installs may have `~/.stockroom/warehouse.duckdb`. Acceptance requires migration implemented **or** explicitly deferred with rationale. Must not silently lose data when both legacy and XDG paths have divergent content; doctor should report active home and legacy presence.

**Why ambiguous:** Auto-migrate on first `home_dir()` / open vs explicit migrate helper / doctor-prompted vs defer entirely for v1 (operators still few). Tradeoffs differ on safety, surprise, and scheduling (cron may point at old log path until reinstall).

**Constraints:** No silent data loss; refuse or warn loudly on divergent dual trees; idempotent if migrate runs; `STOCKROOM_HOME` set → skip legacy migration (explicit override owns the tree); document the choice on the issue if deferred.

## Status

- [ ] Component analysis complete
- [ ] Open questions resolved
- [ ] Test planning complete (TDD)
- [ ] Implementation plan complete
- [ ] Technology validation complete
- [ ] Preflight
- [ ] Build
- [ ] QA
