# Task: fix-cursor-sessionstart-python-bootstrap

* Task ID: fix-cursor-sessionstart-python-bootstrap
* Complexity: Level 2
* Type: bug fix

Move Cursor auto-heal/dashboard from `workspaceOpen` to `sessionStart` (fires on Mac Cursor 3.10.x). Replace bare `python3` hook bootstrap with `uv python find --project … --no-config` so rectify runs under a `>=3.11` interpreter without `uv run --no-sync` (empty-`.venv` footgun). Apply the same bootstrap to Claude’s SessionStart hook.

## Test Plan (TDD)

### Behaviors to Verify

- B1 (Cursor event): load `hooks/cursor-hooks.json` → hooks key is `sessionStart` (not `workspaceOpen`); flat native schema (`version`, top-level `command`, timeout 300); no Claude nesting
- B2 (Cursor stdin): Cursor command still drains stdin (`cat >/dev/null`) before work
- B3 (Bootstrap select): both harness commands use `uv python find --project … --no-config` (or equivalent project-scoped find) and invoke that interpreter as `"$PY" -m stockroom` — not bare `python3`
- B4 (No empty-venv footgun): rectify half must not contain `uv run` / `--no-sync`
- B5 (Order + contract): rectify precedes `stockroom dashboard`; PATH exports `~/.local/bin`; `|| true`; Cursor stderr visible; Claude stderr silenced with stdout
- B6 (Claude parity): Claude SessionStart command uses the same uv-find bootstrap shape with `CLAUDE_PLUGIN_ROOT` / `--owner claude`
- Edge (schema regression): `workspaceOpen` absent from Cursor hooks config; Claude remains nested `SessionStart` / `hooks[]` / `type: "command"`

### Test Infrastructure

- Framework: pytest (engine suite under `skills/sr-search/tests/`)
- Test location: `skills/sr-search/tests/test_packaging.py` (existing hook contract tests)
- Conventions: module-scoped JSON fixtures (`cursor_hooks`, `claude_hooks`); helpers `_hook_command_entries`, `_assert_combined_rectify_then_dashboard`
- New test files: none

## Implementation Plan

1. **Failing packaging tests (TDD)** — rewrite Cursor/Claude hook assertions for `sessionStart` + uv-find bootstrap
   - Files: `skills/sr-search/tests/test_packaging.py`
   - Changes: `_hook_command_entries` reads `sessionStart` for Cursor; `_assert_combined_rectify_then_dashboard` requires `uv python find --project` + `"$PY" -m stockroom` (or documented equivalent), forbids bare `python3` and `uv run` in rectify half; update `test_cursor_hook_schema_and_combined_command` docstring/asserts (event name, no `workspaceOpen`); Claude test expects same bootstrap

2. **Cursor hook JSON** — event + bootstrap
   - Files: `hooks/cursor-hooks.json`
   - Changes: rename key `workspaceOpen` → `sessionStart`; set `APP=…/skills/sr-search`; `PY="$(uv python find --project \"$APP\" --no-config)"`; `PYTHONPATH="$APP/src" "$PY" -m stockroom shim rectify …`; keep `cat >/dev/null`, PATH export, timeout 300, stdout silence, stderr visible, `|| true`

3. **Claude hook JSON** — bootstrap parity only
   - Files: `hooks/claude-hooks.json`
   - Changes: same `uv python find` + `"$PY" -m stockroom` pattern with `CLAUDE_PLUGIN_ROOT` / owner `claude`; keep nested schema and full silence

4. **Docs / briefing altitude** — event + bootstrap wording
   - Files: `docs/using.md`, `memory-bank/systemPatterns.md`, `skills/sr-search/src/stockroom/shim.py` (module docstring)
   - Changes: Cursor auto-launch is `sessionStart`; note uv-find bootstrap (not bare `python3`, not `uv run --no-sync` for rectify)

5. **Verify** — packaging tests then full suite + lint
   - Commands: targeted packaging tests, then `make test` / `make lint` (or project equivalents)

## Technology Validation

No new dependencies. Validated on this machine:

- `uv python find --project <engine> --no-config` returns a usable interpreter (prefers existing `.venv` when present)
- Against a temp project with `pyproject.toml` but **no** `.venv`, find returns a managed `>=3.11` interpreter and does **not** create an empty `.venv`
- `uv python find --no-project --no-config '>=3.11'` also works as a fallback shape; plan prefers `--project` so the pin tracks `requires-python` in `pyproject.toml`

## Dependencies

- `uv` on hook PATH (`$HOME/.local/bin` already exported) — same prerequisite as shim / `sr-initialize`
- At least one `>=3.11` interpreter discoverable by uv (managed or system) — same as engine pin

## Challenges & Mitigations

- **Hook PATH still missing `uv`**: PATH already prefixes `$HOME/.local/bin`; failures stay soft (`|| true`). Mitigate by keeping that export and asserting it in tests.
- **No `>=3.11` installed yet**: `uv python find` fails → rectify skipped; operator runs `sr-initialize` / `uv python install`. Do not fall back to bare `python3` (that reintroduces the Mac 3.9 crash).
- **`sessionStart` fires per composer session** (more often than once-per-workspace): accepted — matches Claude; operator confirmed the event works on Mac; rectify/dashboard remain idempotent.
- **Long inline shell in JSON**: keep one combined command (existing pattern); pin shape in packaging tests rather than extracting a script file (no new artifact owner unless preflight demands it).

## Pre-Mortem

- **Wrong event still doesn’t fire on some Cursor builds**: Operator already verified `sessionStart` on Mac 3.10.x; if WSL/other builds regress, that’s a separate Cursor bug — plan does not keep dual events.
- **“Fix” by rewriting annotations for 3.9 / lowering `requires-python`**: Would fight the engine pin and torch stack; rejected — interpreter selection is the correct layer.
- **Accidentally restore `uv run --no-sync` for rectify**: Empty-`.venv` footgun returns; Challenge + B4 tests already cover — keep the assert that forbids `uv run` in the rectify half.
- **Assume interactive-shell PATH equals hook PATH**: Already disproven on Mac (Xcode 3.9); uv-find is the mitigation.

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Pre-Mortem complete
- [x] Preflight
- [x] Build
- [ ] QA
