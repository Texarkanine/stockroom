# Task: dependabot-config

* Task ID: dependabot-config
* Complexity: Level 2
* Type: simple enhancement

Add `.github/dependabot.yaml` for UV docs (`/`), UV engine (`/skills/sr-search`), and GitHub Actions, using the major-isolation / minor+patch grouping pattern from `a16n` and `inquirerjs-checkbox-search`, with UV cooldown 7 days, GHA no grouping and cooldown opted out (`default-days: 0`), and the four commit prefixes from the brief.

## Test Plan (TDD)

**Operator override (2026-07-15):** No automated tests for `.github/dependabot.yaml`. Platform config is validated by GitHub Dependabot on ingest; pytest contract suites for YAML policy are out of scope.

### Verification (manual / review)

- Three ecosystems: UV `/`, UV `/skills/sr-search`, github-actions `/` (no npm)
- UV groups: minor+patch only (majors ungrouped)
- UV `cooldown.default-days: 7`; GHA `cooldown.default-days: 0` and no `groups`
- Prefixes: `chore(docs)` (+ `prefix-development`), `fix(deps)` / `chore(deps-dev)`, `chore(deps-ci)`

## Implementation Plan

1. ~~Stub/implement pytest contract tests~~ — **cancelled** (operator)
2. **Add Dependabot config** — DONE
   - Files: `.github/dependabot.yaml`
   - Three `updates` entries as specified in the brief; monthly Monday 09:00; assignees `Texarkanine`; PR limits 10 (uv) / 5 (gha)
3. **Documentation** — skipped (no existing Dependabot docs; brief does not require)

## Technology Validation

No new technology — validation not required.

## Dependencies

- Reference configs: `a16n`, `inquirerjs-checkbox-search`, `jekyll-highlight-cards` (prefix style)

## Challenges & Mitigations

- **Docs UV deps in `[dependency-groups]`**: both `prefix` and `prefix-development` set to `chore(docs)`
- **Platform default 3-day cooldown**: GHA uses `default-days: 0`
- **Avoid `include: scope`**: full conventional prefixes embedded

## Pre-Mortem

- Wrong UV roots / omitted GHA cooldown opt-out / double-scoped prefixes — addressed in config as written

## Status

- [x] Initialization complete
- [x] Test planning complete (operator: no automated tests)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Pre-Mortem complete
- [x] Preflight
- [x] Build
- [ ] QA
