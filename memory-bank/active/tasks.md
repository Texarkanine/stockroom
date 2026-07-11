# Task: dashboard-port-58008

* Task ID: dashboard-port-58008
* Complexity: Level 2
* Type: simple enhancement

Change the dashboard default port from `6767` to `58008` via find/replace across the working tree. No migration for existing hosts. Exclude `memory-bank/archive/` (history) and `skills/sr-search/uv.lock` (hash substrings that contain `6767`).

## Test Plan (TDD)

### Behaviors to Verify

- [B1 DEFAULT_PORT]: `stockroom.dashboard.__main__.DEFAULT_PORT` → `58008`
- [B2 serve default]: `dashboard.server.serve` signature / call with no port → binds `58008` (default kwarg)
- [B3 CLI default URL]: `main([])` with free port → prints `http://127.0.0.1:58008/` and spawns with `--port 58008`
- [B4 identity helpers]: identity path/read/write tests that used port `6767` as the fixture port → use `58008` (same contracts, new default)
- [B5 docs/skills]: `sr-dashboard` skill and `docs/using.md` advertise `58008` as the default URL/port
- [B6 no archive edits]: `memory-bank/archive/` still contains historical `6767` references unchanged
- [B7 uv.lock intact]: `uv.lock` hashes that happen to contain the digit sequence `6767` are not rewritten

### Test Infrastructure

- Framework: pytest (configured in `skills/sr-search/pyproject.toml`)
- Test location: `skills/sr-search/tests/`
- Conventions: `test_dashboard_cli.py`, `test_dashboard_identity.py`; inject probe/spawn/identity fakes
- New test files: none — update existing assertions; optionally add a one-liner asserting `DEFAULT_PORT == 58008` in `test_dashboard_cli.py` if no existing constant assertion

## Implementation Plan

1. [x] **Failing constant assertion (TDD entry)**
   - Files: `skills/sr-search/tests/test_dashboard_cli.py`
   - Changes: add/adjust assertion that `DEFAULT_PORT == 58008` (and/or default CLI URL uses 58008); run targeted tests — expect fail while code still says 6767

2. [ ] **Find/replace port in engine + tests**
   - Files: `skills/sr-search/src/stockroom/dashboard/__main__.py`, `skills/sr-search/src/stockroom/dashboard/server.py`, `skills/sr-search/tests/test_dashboard_cli.py`, `skills/sr-search/tests/test_dashboard_identity.py`
   - Changes: replace `6767` → `58008` (DEFAULT_PORT, `serve` default, test fixtures/URLs). Prefer a scoped sed/script over hand edits; do not touch `uv.lock`

3. [ ] **Find/replace docs, skill, tech context**
   - Files: `skills/sr-dashboard/SKILL.md`, `docs/using.md`, `memory-bank/techContext.md`
   - Changes: default URL/port prose `6767` → `58008`. Leave `memory-bank/archive/` and `memory-bank/active/` task narrative alone (active describes the *change from* 6767)

4. [ ] **Verify**
   - Run targeted dashboard CLI/identity tests, then full `make ci` (or project-equivalent)
   - Spot-check: `rg 6767` outside archive/active/uv.lock returns no hits (or only intentional non-default ports if any remain)

## Technology Validation

No new technology - validation not required

## Dependencies

- Existing `DEFAULT_PORT` / `serve(port=...)` / identity port-scoped files — no new APIs
- Session-start hook invokes `stockroom dashboard` without `--port` — picks up new default automatically

## Challenges & Mitigations

- **Challenge: blind repo-wide sed corrupts `uv.lock` hashes containing `6767`.** Mitigation: exclude `skills/sr-search/uv.lock` (and preferably lock any other binary/hash artifacts) from the replace set.
- **Challenge: sed of `memory-bank/active/` turns “change from 6767 to 58008” into nonsense.** Mitigation: exclude `memory-bank/active/` and `memory-bank/archive/`; only update `memory-bank/techContext.md` among memory-bank files.
- **Challenge: tests use `6767` as a fixture port, not only as DEFAULT_PORT.** Mitigation: replacing fixture ports with `58008` is fine and keeps the suite consistent with the new default; leave intentional alternate ports (`7777`, `8888`) alone.

## Pre-Mortem

- **Plan failed because a global sed rewrote lockfile hashes and broke installs:** already covered by Challenge on `uv.lock` exclusion — make the replace command path-scoped, not `rg -l 6767 | xargs sed`.
- **Plan failed because we “migrated” identity/launcher behavior instead of a constant swap:** hold the brief — no cross-port kill, no dual-port logic; orphaned 6767 listeners are accepted.
- **Plan failed because docs/skills still teach 6767 after code changed:** covered by implementation step 3 as required acceptance work, not optional polish.

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Pre-Mortem complete
- [ ] Preflight
- [ ] Build
- [ ] QA
