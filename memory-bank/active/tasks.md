# Current Task: nightly-ensure-env

**Complexity:** Level 1

## Fix

The nightly payload was `(date; stockroom ingest && stockroom embed)`. An exact `uv sync` (from `make test`, `make format`, and the pre-commit hook) uninstalls torch, and the unattended job never ran `stockroom shim ensure-env`, so embed died with `ModuleNotFoundError: No module named 'torch'` while ingest had already succeeded.

`render_payload` now renders `(date; stockroom shim ensure-env; stockroom ingest && stockroom embed)`. The `;` keeps a failed heal from skipping ingest. The `&&` still skips embed when ingest fails. Cron and launchd both use that one payload, so `schedule status` reports a pre-change entry as `up-to-date: no`.

## Files

- `skills/sr-search/src/stockroom/schedule.py`
- `skills/sr-search/tests/test_schedule.py`
- `skills/sr-search/src/stockroom/__main__.py`
- `skills/sr-search/src/stockroom/backfill/__main__.py`
- `skills/sr-initialize/SKILL.md`
- `docs/architecture/backfill.md`
- `docs/architecture/index.md`
- `docs/architecture/lifecycle.md`
- `docs/user-guide/load/schedule.md`

## QA Result (2026-10-20) — PASS

Semantic review of the implementation against `projectbrief.md` (issue #146). No code edits made during QA.

- KISS: PASS — one string change in the single owner (`render_payload`); no new abstraction.
- DRY: PASS — cron, launchd, and `schedule status` all consume the one rendering; test helpers reuse `render_payload` shape.
- YAGNI: PASS — no speculative code; the `fail=` hook in the fake shim exists only for the failure-grouping tests.
- Completeness: PASS — exact payload string, `;` before ingest / `&&` before embed, `%`-free assert, `shlex.quote` log path, both schedulers, stale-entry status, space- and quote-path coverage all present.
- Regression: PASS — backfill absence guarantee intact (97 backfill tests pass); `ingest` acquires no `backfill` import edge; help/doc text updated to match.
- Integrity: PASS — no hardcoded paths, magic numbers, or debug artifacts.
- Documentation: PASS — `sr-initialize` skill, both `__main__` help strings, and all four docs pages that quoted the old command now describe the heal-first sequence.
- Advisory (non-blocking): untracked `.cursor/skills/stockroom-local/` is a stray local artifact untouched by this diff; not judged as part of this task.
