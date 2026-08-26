# Task: cursor-model-ingest

* Task ID: cursor-model-ingest
* Complexity: Level 2
* Type: bug fix

Cursor `sessions.models` go dark after ~2026-08-20 because WSL enrichment discovery aborts on a stale `/mnt/<letter>` (`ENXIO` on `/mnt/i` here) and never opens the live Windows `ai-code-tracking.db`. Cursor's tracking schema did not change. Keep the existing `ai_code_hashes` / `conversation_summaries` reader; make the `/mnt` walk fail-soft per entry so one dead drive letter cannot hide sibling homes.

## Diagnosis

- Warehouse: Cursor transcripts after 2026-08-20 have `models` NULL (87 sessions on the 20th with 4 still filled; 0 filled from the 21st on). Almost all of those rows are agent-transcripts, not chats.
- Linux `~/.cursor/ai-tracking/ai-code-tracking.db` last wrote 2026-08-08 (11 conversations). The enricher finds this file and stops.
- Live IDE DB is `/mnt/s/Users/Austin/.cursor/ai-tracking/ai-code-tracking.db` (31MB, still written today). Same tables/columns Stockroom already reads (`ai_code_hashes.conversationId` + `model`). Direct `read_enrichment` on that path returns models for current conversation ids (e.g. this session → `grok-4.6`).
- `_wsl_windows_candidate_paths` does `sorted(p for p in Path("/mnt").iterdir() if p.is_dir())`. On this machine that raises `[Errno 19] No such device: '/mnt/i'` and the function returns `[]`, so `resolve_db_paths` never unions the Windows DB.
- Chats `lastUsedModel` is not the cliff (5 chats since August 1, all still have models).

Backwards compatibility is already true for the SQL reader. The required patch is discovery robustness, not a second Cursor format.

## Test Plan (TDD)

### Behaviors to Verify

- Stale drive letter: `/mnt` contains a child whose `is_dir()` (or equivalent stat) raises `OSError` (e.g. `ENXIO`) and a sibling `…/Users/<name>/.cursor/ai-tracking/ai-code-tracking.db` → walker still returns that sibling path (modern and, if present, legacy).
- Users listing failure: one drive's `Users/` listing raises `OSError` and another drive has a readable tracking DB → walker still returns the readable DB.
- User-home stat failure: one `Users/*` child raises `OSError` on `is_dir()` and a sibling user has a tracking DB → walker still returns the sibling DB.
- Missing `/mnt`: `mnt` path is not a directory → walker returns `[]` and does not raise.
- Drive without `Users/`: skipped; other drives still contribute.
- Existing schema: `read_enrichment` on `ai_code_hashes` (+ optional `conversation_summaries`) is unchanged — first-seen model order, fail-soft missing file/tables.
- Empty/null `model` or `conversationId` rows still do not enter the map (`_append_model`).

### Test Infrastructure

- Framework: pytest (+ xdist) as configured in `skills/sr-search/pyproject.toml`
- Test location: `skills/sr-search/tests/test_ingest_enrich.py` (extend; do not add a parallel suite)
- Conventions: one behavior per `test_*` function; `tmp_path` fixtures; monkeypatch `STOCKROOM_AI_TRACKING_DB` / `Path.home` only when testing resolve/load, not when testing the walker itself
- New test files: none

## Implementation Plan

1. [x] Add failing walker tests (injectable `mnt` root; do not mock `_wsl_windows_candidate_paths` for these cases)
   - Files: `skills/sr-search/tests/test_ingest_enrich.py`
   - Changes: tests for the behaviors above using a `tmp_path` stand-in for `/mnt` and a targeted `Path.is_dir` (or helper) monkeypatch that raises `OSError(errno.ENXIO, …)` on the stale child only
2. [x] Fail-soft `/mnt` walk
   - Files: `skills/sr-search/src/stockroom/ingest/enrich.py`
   - Changes: give `_wsl_windows_candidate_paths` an optional `mnt: Path | None = None` (default `Path("/mnt")`). Replace `Path.iterdir()` + unguarded `is_dir()` list-comps with a helper that lists names via `os.listdir` (does not stat) and stats each child in its own `try`/`except OSError`. Use that helper for both `/mnt` drive letters and each `Users/` listing. Keep modern + legacy candidate paths. Do not change `read_enrichment` SQL.
3. [x] Confirm existing enrich/orchestrator tests still pass (schema reader + merge/pin/env override)
   - Files: `skills/sr-search/tests/test_ingest_enrich.py`, `skills/sr-search/tests/test_ingest_orchestrator.py`
   - Changes: none expected unless a signature leak requires callers to stay defaulted
4. [x] Document the skip-dead-letter behavior
   - Files: `docs/user-guide/load/sources.md`
   - Changes: one sentence under Cursor `sessions.models` enrichment — a stale `/mnt/<letter>` is skipped so other Windows homes are still merged. No new config keys.
5. [ ] Operator restore of already-written NULL rows (no code)
   - After the walker fix, incremental ingest only rewrites sessions whose source mtime advances. A one-shot `stockroom ingest --full` is required to refill `models` on Aug 20+ rows that are already in the warehouse.

## Technology Validation

No new technology - validation not required

## Dependencies

- Existing: stdlib `os` / `pathlib` / `sqlite3` in `stockroom.ingest.enrich`
- Operator: one `--full` ingest after the fix to backfill already-NULL Cursor sessions

## Challenges & Mitigations

- `Path.iterdir()` can raise on the broken child before siblings are yielded: do not catch only the outer `iterdir()`; list names first (`os.listdir`), then stat each name.
- Tests cannot create a real drvfs `ENXIO` mount: inject `mnt` and raise `OSError` from `is_dir` (or the helper's stat) for one child name.
- `write_session` is delete-then-insert: once discovery works, a later incremental rewrite of a grown transcript will refill `models`. Completed sessions that never change stay NULL until `--full` — call that out rather than adding a one-off backfill command.

## Pre-Mortem

- Plan assumed a Cursor schema change and rewrote the SQL reader: already rejected; keep `read_enrichment` as-is.
- Fix only the Linux `~/.cursor` candidate: would not restore IDE models; the live DB is the WSL Windows home.
- Tests keep mocking `_wsl_windows_candidate_paths` for the new cases: the OSError path would never run; new tests must call the real walker.
- Ship the walker fix and skip `--full`: dashboard/SQL stay empty for Aug 20–25 until those transcripts grow.

## QA Results

Verdict: **PASS** (semantic review vs plan; two trivial docstring fixes applied)

- KISS/DRY/YAGNI: clean — `_iter_dirs` is a flat helper with two callsites (drive letters + `Users/` listing); `mnt` param is plan-required, test-used, and keeps all nine existing `lambda: []` mocks valid (sole production callsite passes no args).
- Completeness: plan steps 1–4 implemented as written; step 5 (`stockroom ingest --full`) is operator-only and correctly open. All five walker behaviors tested against the **real** walker (no walker mocks). `read_enrichment` SQL has zero diff hunks vs `321a506`.
- Regression: style indistinguishable from module (`Path | None = None` resolve-inside mirrors `_candidate_db_paths`; `except OSError` per entry; deterministic sort preserved). Docs sentence sits under Cursor `sessions.models` enrichment, no new config keys, does not overclaim.
- Trivial fixes applied (Integrity): "cannot be stated" → "cannot be statted" in `_iter_dirs` docstring (`enrich.py`) and `test_wsl_walker_skips_unstatable_user_home` docstring.
- Non-blocking observations (pre-existing, out of plan scope — for Reflect):
  - `_append_model` null/empty guard has no direct test anywhere (fixture seeds only non-null rows); path unchanged by this build.
  - Two residual unguarded stats of the same failure class remain: `mnt.is_dir()` at walker entry (raises if `/mnt` itself is unstatable, e.g. EACCES/ENXIO) and `resolve_db_paths._add`'s `normalized.is_file()` (TOCTOU if a drive goes stale between discovery and the existence check). Both unlikely; fixing them is a TDD'd behavior change, not a QA fix.
- Verification: ruff check + format clean on both touched files; `pytest tests/test_ingest_enrich.py -k wsl_walker -n0` 5/5; full engine suite 821 passed / 4 skipped (independently re-run at QA).

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Pre-Mortem complete
- [x] Preflight
- [x] Build
- [x] QA
