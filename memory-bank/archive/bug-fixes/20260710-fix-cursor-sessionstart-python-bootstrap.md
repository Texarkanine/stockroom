---
task_id: fix-cursor-sessionstart-python-bootstrap
complexity_level: 2
date: 2026-07-10
status: completed
---

# TASK ARCHIVE: fix-cursor-sessionstart-python-bootstrap

## SUMMARY

Moved Cursor auto-heal/dashboard from `workspaceOpen` to `sessionStart` (fires on Mac Cursor 3.10.x) and replaced bare `python3` hook bootstrap with `uv python find --project … --no-config` so rectify runs under a `>=3.11` interpreter. Applied the same bootstrap to Claude’s SessionStart hook without restoring `uv run --no-sync` (empty-`.venv` footgun). Shipped in [#23](https://github.com/Texarkanine/stockroom/pull/23).

## REQUIREMENTS

1. Cursor hook event: `sessionStart` (not `workspaceOpen`); flat native schema preserved.
2. Bootstrap selects a `>=3.11` interpreter via uv — not bare system `python3` (Xcode 3.9 crash on `list[str] | None`).
3. Do not use `uv run --no-sync` for the rectify half.
4. Preserve hook contract: idempotent, fire-and-forget, PATH includes `~/.local/bin`, Cursor stderr visible.
5. Claude SessionStart gets the same bootstrap; packaging tests and docs updated.

## IMPLEMENTATION

### Bootstrap shape

```bash
APP=…/skills/sr-search
PY=$(uv python find --project "$APP" --no-config)
PYTHONPATH="$APP/src" "$PY" -m stockroom shim rectify …
```

Then on-path `stockroom dashboard`. Unquoted `PY=$(…)` is fine for space-free plugin hash paths.

### Key files

| Area | Files |
| --- | --- |
| Cursor hook | `hooks/cursor-hooks.json` (`sessionStart`, uv-find bootstrap) |
| Claude hook | `hooks/claude-hooks.json` (bootstrap parity; nested schema unchanged) |
| Tests | `skills/sr-search/tests/test_packaging.py` |
| Docs | `docs/using.md`, `memory-bank/systemPatterns.md`, `shim.py` module docstring |

## TESTING

- TDD: packaging contract tests for `sessionStart`, uv-find bootstrap, no bare `python3`, no `uv run` in rectify half, Claude parity.
- Full suite: **467 passed, 3 skipped**; ruff clean.
- `/niko-qa` semantic review PASS; no fixes needed.

## LESSONS LEARNED

### Technical

- Hook bootstrap and engine invocation are different layers: the shim already used uv; the Mac 3.9 crash was only the PYTHONPATH `python3` entry. Prefer `uv python find --project` over restoring `uv run --no-sync` for rectify.

### Process

Nothing notable beyond plan accuracy — technology validation matched build reality.

### Million-dollar question

If session-start auto-heal had assumed “uv selects the interpreter; never bare `python3`” from day one, we would have skipped the `workspaceOpen` detour and the Xcode-3.9 footgun. What we built is that elegant form for the hook layer.

## PROCESS IMPROVEMENTS

None — plan, preflight, build, and QA held without amendment.

## TECHNICAL IMPROVEMENTS

None beyond the shipped bootstrap. Out of scope (advisory): `sr-initialize` still uses bare `python3` in an interactive shell.

## NEXT STEPS

None. Task complete and archived.
