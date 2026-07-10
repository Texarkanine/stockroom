# Progress

Adopt XDG Base Directory layout for stockroom-owned data on all Unix-like platforms (Linux, WSL, macOS), with `STOCKROOM_HOME` override preserved, a safe legacy `~/.stockroom/` migration path, doctor reporting, docs/skills updates, and tests — as specified in [issue #3](https://github.com/Texarkanine/stockroom/issues/3).

**Complexity:** Level 3

## 2026-07-09 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - Validated intent against issue #3
    - Classified as Level 3 Intermediate Feature
    - Populated ephemeral memory-bank files (`projectbrief`, `activeContext`, `tasks`, `progress`)
* Decisions made
    - Level 3 (not L2): multiple components + migration/conflict design + docs surface; Level 4 unjustified — no multi-subsystem architectural redesign
* Insights
    - Issue already frames open design points (single tree vs split data/state; migrate now vs defer) that belong in creative/plan before build

## 2026-07-09 - PLAN - IN-PROGRESS

* Work completed
    - Loaded Level 3 plan procedure; surveyed `warehouse.py`, `schedule.py`, `doctor.py`, tests, O1 / memory-bank path language
    - Flagged Q1 (layout shape) and Q2 (legacy migration) as creative-phase open questions
* Decisions made
    - Canonical code lives under `skills/`; `.cursor/skills/stockroom-local` is localdev symlink only (not a second edit target)
* Insights
    - `home_dir()` mkdir-on-resolve means naive XDG defaults would create empty XDG dirs even when legacy still holds data — migration/detection order matters

## 2026-07-09 - CREATIVE - COMPLETE (xdg layout shape)

* Work completed
    - Architecture exploration of single data tree vs split data/state vs symlink compat
* Decisions made
    - **Single tree under `$XDG_DATA_HOME/stockroom/`** (default `~/.local/share/stockroom/`), including logs — see `creative-xdg-layout-shape.md`
* Insights
    - Issue already permits keeping logs under data home; STATE split is premature for a regenerable log

## 2026-07-09 - CREATIVE - COMPLETE (legacy home migration)

* Work completed
    - Architecture exploration of auto-migrate vs explicit CLI vs defer vs init-only
* Decisions made
    - **Safe auto-migrate at path resolve** when unambiguous; hard refuse when both warehouses exist and diverge; doctor reports home + legacy facts — see `creative-legacy-home-migration.md`
* Insights
    - Detection must run before mkdir so an empty XDG tree never masquerades as “already migrated”

## 2026-07-09 - PLAN - COMPLETE

* Work completed
    - Component analysis across warehouse / doctor / schedule / docs
    - TDD map for XDG resolution, migration, conflict, doctor facts
    - Ordered 7-step implementation plan in `tasks.md`
* Decisions made
    - Doctor uses pure `inspect_homes()` (no migrate on probe); only `home_dir()` migrates
    - Living docs + O1/brainstorm reconciliation in scope; historical archives left as-is
    - Spike `export_dataset.py` default path aligned as a docs/consistency edit
* Insights
    - Schedule needs no API change under the single-tree decision; risk is stale installed log paths, handled by docs/doctor warning
