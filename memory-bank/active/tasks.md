# Task: p4-dashboard / m3 — Launch surfaces

* Task ID: p4-dashboard-m3
* Complexity: Level 2
* Type: simple enhancement

Wire the already-shipped dashboard launcher into the three operator-facing surfaces: the `python -m stockroom` dispatcher (`dashboard` subcommand), a thin `sr-dashboard` wrapper skill that prints the local URL, and one combined session-start hook per harness that rectifies the shim then launches the dashboard. Correct planning-doc ports from 3143 → 6767. No new server or front-end logic — m1/m2 already own those.

## Test Plan (TDD)

### Behaviors to Verify

- **Dispatcher registration**: `stockroom --help` lists `dashboard` → expected outcome: exit 0 and stdout contains the `dashboard` token.
- **Dispatcher help forward**: `stockroom dashboard --help` → exit 0 and stdout carries a dashboard-module fingerprint (`--foreground` or `Launch`).
- **Skill hygiene**: `skills/sr-dashboard/SKILL.md` exists and contains only `stockroom dashboard` (or `stockroom dashboard …`) as the engine invocation → no forbidden tokens (`APP_DIR`, `PYTHONPATH`, `uv run`, `--no-sync`, `--no-config`, `python -m stockroom`, plugin-root vars, `find -L`).
- **Missing shim guidance**: skill text tells the agent that a missing `stockroom` on PATH means run `sr-initialize` → no fallback incantation.
- **Cursor combined hook**: exactly one `sessionStart` command entry → silenced (`>/dev/null 2>&1`), timed out, contains `shim rectify` with `--owner cursor` and `${CURSOR_PLUGIN_ROOT}`, and contains `stockroom dashboard`, with rectify appearing before dashboard in the command string.
- **Claude combined hook**: exactly one `SessionStart` command entry → same shape with `--owner claude` and `${CLAUDE_PLUGIN_ROOT}`.
- **Hook still never errors**: each harness command ends with `|| true` (or equivalent whole-command silence+swallow) so a missing shim / busy port cannot fail session start.
- **Port docs**: `planning/roadmap.md` and `planning/tech-brief.md` contain `6767` as the dashboard port and do not cite `3143` as a port (lockfile hash substrings elsewhere are out of scope).
- **On-path launch half**: in each harness hook command, the substring `stockroom dashboard` is not preceded on the same half by `uv run` / `PYTHONPATH=` / `python -m stockroom` — i.e. launch is on-path after rectify, not folded into the bootstrap incantation.

### Edge Cases

- **Unknown subcommand still clean**: `stockroom bogus` → exit 2, names token, no traceback (existing; must not regress when `SUBCOMMANDS` grows).
- **Empty / pre-init machine**: hook command must not assume a healthy on-path shim for the *rectify* half (chicken-egg: a dead baked `APP_DIR` means `stockroom` itself cannot run). Rectify keeps the existing plugin-root `PYTHONPATH`+`uv run`+`python -m stockroom shim rectify` bootstrap; only the *launch* half uses on-path `stockroom dashboard`.
- **Idempotent launch**: not re-tested here — owned by `tests/test_dashboard_cli.py` (probe/spawn/EADDRINUSE). Hook tests assert the command string invokes `stockroom dashboard`, not platform daemonization.
- **Two hooks vs one**: packaging tests assert a single command entry per harness (combined sequencing), not a second separate hook group.

### Test Infrastructure

- Framework: pytest (engine) under `skills/sr-search/tests/`
- Test location: `skills/sr-search/tests/`
- Conventions: subprocess CLI tests (`test_dispatcher_cli.py` pattern); packaging JSON contract tests (`test_packaging.py` + `repo_root` fixture); skill hygiene scans committed `SKILL.md` files for forbidden tokens
- New test files: none — extend existing suites
- Extend:
  - `tests/test_dispatcher_cli.py` — add `"dashboard"` to `SUBCOMMANDS` tuple; add fingerprint `"--foreground"` (or `"Launch"`) in `fingerprints`
  - `tests/test_skill_hygiene.py` — add `"sr-dashboard"` to `WRAPPER_SKILLS`
  - `tests/test_packaging.py` — extend cursor/claude hook tests for combined rectify-then-dashboard sequencing, single entry, and on-path launch (assert `stockroom dashboard` appears after `shim rectify` and is not wrapped in the `uv run`/`PYTHONPATH` bootstrap); add a small port-doc contract asserting `planning/roadmap.md` and `planning/tech-brief.md` mention `6767` and do not mention port `3143`

## Implementation Plan

1. **Failing dispatcher tests**
   - Files: `skills/sr-search/tests/test_dispatcher_cli.py`
   - Changes: add `"dashboard"` to `SUBCOMMANDS`; add fingerprint entry for `dashboard` help. Run — expect fail (subcommand absent from `__main__.py`).

2. **Register `dashboard` in the dispatcher**
   - Files: `skills/sr-search/src/stockroom/__main__.py`
   - Changes: add `"dashboard": ("stockroom.dashboard.__main__", "Launch the read-only local dashboard.")` to `SUBCOMMANDS`. Run dispatcher tests — pass.

3. **Failing skill-hygiene coverage**
   - Files: `skills/sr-search/tests/test_skill_hygiene.py`
   - Changes: add `"sr-dashboard"` to `WRAPPER_SKILLS`. Run — expect fail (skill directory missing).

4. **Create thin `sr-dashboard` skill**
   - Files: `skills/sr-dashboard/SKILL.md` (new)
   - Changes: mirror `sr-query`/`sr-semantic` shape — YAML front-matter (`name`, `description`, `enable-model-invocation: true`), when-to-use, `stockroom dashboard` as the sole engine invocation, missing-shim → `sr-initialize`, pointer to `../sr-search/references/system-model.md`, short guardrails (prints URL; do not pass `--foreground` from the skill; relay URL to user). Run hygiene tests — pass.

5. **Failing hook + port-doc packaging tests**
   - Files: `skills/sr-search/tests/test_packaging.py`
   - Changes: extend `test_cursor_hook_schema_and_rectify_command` / `test_claude_hook_schema_and_rectify_command` (or rename to combined-hook names) to assert: exactly one command entry; `stockroom dashboard` present; `cmd.find("shim rectify") < cmd.find("stockroom dashboard")`; the launch token is not inside the `uv run`/`PYTHONPATH` bootstrap (on-path after rectify); silence + timeout preserved; plugin-root + owner assertions preserved for the rectify half. Add `test_planning_docs_use_dashboard_port_6767` reading `planning/roadmap.md` and `planning/tech-brief.md` via `repo_root`, asserting `6767` is present and `3143` is absent. Run — expect fail.

6. **Combine rectify-then-launch in both hook configs**
   - Files: `hooks/cursor-hooks.json`, `hooks/claude-hooks.json`
   - Changes: keep a **single** command entry per harness. Command shape (Cursor; Claude swaps root/owner):
     - Rectify half (bootstrap, unchanged mechanism): existing `PYTHONPATH=… uv run … python -m stockroom shim rectify --owner cursor --app-dir "${CURSOR_PLUGIN_ROOT}/skills/sr-search"`
     - Launch half (on-path): `stockroom dashboard`
     - Whole command silenced and non-failing: `… >/dev/null 2>&1 || true` covering both halves (e.g. `{ rectify; stockroom dashboard; } >/dev/null 2>&1 || true` or sequential `… || true; stockroom dashboard >/dev/null 2>&1 || true`). Prefer one silence wrapper so session start never surfaces output.
   - Rationale (chicken-egg): rectify cannot depend solely on the on-path shim — a stale baked `APP_DIR` makes `stockroom` itself unusable; the plugin-root bootstrap is the only heal path. After rectify, launch goes through the healed shim. Run hook packaging tests — pass; port-doc test still fails.

7. **Correct planning-doc ports**
   - Files: `planning/roadmap.md`, `planning/tech-brief.md`
   - Changes: replace port `3143` with `6767` at the three narrative sites (roadmap prose + milestone bullet; tech-brief Dashboard section). Do not touch `uv.lock` hash substrings. Run port-doc packaging test — pass.

8. **Full verification**
   - Files: none (gate)
   - Changes: run `make ci` from repo root (pytest + reuse + lint). Manual smoke (QA phase): with shim installed, `stockroom dashboard` prints `http://127.0.0.1:6767/`; second invocation is a no-op probe; confirm hook JSON still parses as valid JSON.

## Technology Validation

No new technology — validation not required. Reuses existing dispatcher, dashboard launcher (`stockroom.dashboard.__main__`), shim rectify, hook JSON schemas, and skill hygiene scanner.

## Dependencies

- m1 dashboard launcher (`stockroom.dashboard.__main__.main`, port 6767, probe/spawn) — already shipped
- m2 static front-end — already shipped (served by m1; launch surfaces do not touch it)
- Phase-3 on-path shim + `shim rectify` contract — already shipped
- Existing packaging / dispatcher / hygiene test suites

## Challenges & Mitigations

- **Chicken-egg on hook rectify**: A dead on-path shim cannot heal itself via `stockroom shim rectify`. **Mitigation**: keep plugin-root bootstrap for rectify; use on-path `stockroom dashboard` only for launch. Document in hook command comments is unnecessary (JSON); capture the rationale in this plan and in reflect.
- **Roadmap wording vs amended hook discipline**: Roadmap still says the hook "launches it and nothing else" / "one-liner carrying no invocation plumbing." Milestone scope only requires port corrections. **Mitigation**: do not expand doc scope in build unless a one-line narrative fix is free adjacent to the port edit; otherwise leave narrative alignment for reflect/capstone.
- **Test ROI**: Do not write tests that Python can daemonize or that Cursor/Claude fire hooks. **Mitigation**: packaging asserts command *shape*; dashboard CLI tests already own probe/spawn; QA does one manual `stockroom dashboard` smoke.
- **Skill over-teaching**: Skill must not document `--foreground` / internal spawn as normal agent usage. **Mitigation**: skill says "run `stockroom dashboard`, print the URL"; leave flags to `stockroom dashboard --help`.

## Preflight Amendments

- Port-doc correction is now an explicit failing packaging test before the doc edit (was build-step/manual only).
- Hook packaging asserts the launch half stays on-path (`stockroom dashboard` after rectify, not folded into `uv run`/`PYTHONPATH` bootstrap).

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Preflight
- [ ] Build
- [ ] QA
