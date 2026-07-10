---
task_id: fix-cursor-sessionstart-python-bootstrap
date: 2026-07-10
complexity_level: 2
---

# Reflection: fix-cursor-sessionstart-python-bootstrap

## Summary

Moved Cursor auto-heal/dashboard to `sessionStart` and replaced bare `python3` bootstrap with `uv python find --project` on both harnesses. Delivered to plan; suite green; QA clean.

## Requirements vs Outcome

All brief requirements met: Cursor event rename, uv-mediated `>=3.11` interpreter selection, no `uv run --no-sync` for rectify, Claude bootstrap parity, packaging tests and docs updated. Nothing added or dropped.

## Plan Accuracy

Plan sequence and file list held. Technology validation (`uv python find` without empty `.venv`) matched build reality. No surprises beyond shell quoting for `PY=$(…)` (unquoted substitution — fine for plugin hash paths).

## Build & QA Observations

TDD red→green on packaging tests was straightforward. Full suite and ruff clean on first full run. QA found nothing to fix.

## Insights

### Technical
- Hook bootstrap and engine invocation are different layers: the shim already used uv; the Mac 3.9 crash was only the PYTHONPATH `python3` entry. Prefer `uv python find --project` over restoring `uv run --no-sync` for rectify.

### Process
- Nothing notable

### Million-Dollar Question

If session-start auto-heal had assumed “uv selects the interpreter; never bare `python3`” from day one, we would have skipped the workspaceOpen detour and the Xcode-3.9 footgun. What we built is that elegant form for the hook layer.
