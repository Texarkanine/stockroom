# Active Context

## Current Task: issue-130-root-lock-hermetic
**Phase:** BUILD - COMPLETE

## What Was Done
- QA FAIL: leftover bare `uv run properdocs serve --no-strict` in contributing docs.
- Fixed that command and the root `pyproject.toml` header comments to include `--no-config`.
- Contributing docs now also forbid bare `uv run` at repo root.

## Next Step
- Re-run Level 1 QA via a fresh subagent.
