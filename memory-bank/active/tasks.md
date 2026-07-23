# Task: cursor-ai-tracking-multi-db

* Task ID: cursor-ai-tracking-multi-db
* Complexity: Level 2
* Type: bug fix (multi-source enrich)

Fix [#82](https://github.com/Texarkanine/stockroom/issues/82): Cursor `sessions.models` enrichment currently uses first-hit `default_db_path()`, so a tiny WSL `~/.cursor/ai-tracking/ai-code-tracking.db` shadows the Windows IDE tracking DB. Change enrich to walk/merge all readable discovery candidates (fail-soft), add optional additive XDG `[cursor].ai_tracking_dbs`, keep `STOCKROOM_AI_TRACKING_DB` / ingest `ai_tracking_db=` as single-DB overrides. Create XDG config machinery fresh on this branch (reference aborted `enhance-cursor-tokens` for shape only; do **not** ship `state_vscdb`).

## Test Plan (TDD)

### Behaviors to Verify

- **Walk-all discovery**: modern home DB + WSL candidate both exist → `resolve_db_paths()` returns both (not first-hit only).
- **Merged enrich (disjoint IDs)**: two synthetic DBs with disjoint `conversationId`s → merged map contains both conversations' models.
- **Shadowing regression**: home modern DB (CLI id) + second candidate (IDE id) → merge includes IDE models (first-hit would drop them).
- **Env single-DB override**: `STOCKROOM_AI_TRACKING_DB` set → resolution is exactly that one path; other candidates ignored.
- **Ingest kwarg override**: `ai_tracking_db=` still forces a single path (tests/one-shots unchanged).
- **Config pins additive**: XDG `[cursor].ai_tracking_dbs` path not in discovery → included in resolve set; discovery paths still included.
- **Config fail-soft**: missing `config.toml`, malformed TOML, missing pin path, unreadable pin → empty/skip that source, never raise; other DBs still enrich.
- **Dedup paths**: same path via discovery and pin → read once.
- **Cross-DB model de-dupe**: overlapping conversationId with same model string → one entry (first-seen across walk order).
- **Absent everything**: no files, no config → empty enrichment (orchestrator still runs).
- **Orchestrator default multi-DB**: with no env/kwarg override, patched discovery returning two disjoint DBs → ingest writes `sessions.models` for both conversation ids (AC1/AC3).
- **Regression**: existing single-DB `read_enrichment` schema/order/malformed behaviors unchanged.
- **Docs**: ingest user-guide describes multi-DB merge, additive `ai_tracking_dbs`, and env single-DB override semantics.

### Test Infrastructure

- Framework: pytest (+ pytest-xdist) under `skills/sr-search/`
- Test location: `skills/sr-search/tests/`
- Conventions: `test_*.py`; enrich path tests monkeypatch `Path.home` / `_wsl_windows_candidate_paths` / env; synthetic sqlite DBs via `tmp_path` + `sqlite3` (see `test_ingest_enrich.py` / `ai_tracking_db` fixture)
- New/extended test files:
  - `tests/test_config.py` (XDG config home + settings)
  - extend `tests/test_ingest_enrich.py` (resolve set + merge)
  - extend `tests/test_ingest_orchestrator.py` (default multi-DB → `sessions.models`)

## Implementation Plan

Each numbered unit is one TDD cycle: **(a) write/adjust failing tests → (b) run and confirm fail → (c) implement → (d) run and confirm pass**. Do not start (c) until (a)/(b) are done for that unit.

1. **XDG config home**
   - (a) Tests in `tests/test_config.py`: `XDG_CONFIG_HOME` → `$XDG_CONFIG_HOME/stockroom`; unset → `~/.config/stockroom`; pure (no mkdir).
   - (c) Add `resolve_config_home()` + source labels to `skills/sr-search/src/stockroom/home.py` (aborted-branch pattern; stdlib-only). Optionally re-export from `warehouse.py` only if existing home re-exports make that the convention for callers — prefer importing `stockroom.home` directly from config/enrich.

2. **Fresh `stockroom.config`**
   - (a) Tests: missing/malformed/empty → empty `Settings`; valid `[cursor].ai_tracking_dbs` string list → `tuple[Path, ...]`; ignore non-strings/empties; **no** `state_vscdb` field on `Settings`.
   - (c) New `skills/sr-search/src/stockroom/config.py`: `Settings(cursor_ai_tracking_dbs=())`, `load_settings()` via `tomllib`, fail-soft.

3. **Resolve path set**
   - (a) Replace first-hit-only expectations in `test_ingest_enrich.py` with: walk-all returns both home+WSL when present; env override singleton; config pin additive + dedupe; absent → empty list or conventional fallback policy as designed.
   - (c) In `enrich.py`: `resolve_db_paths()` = env → `[path]`; else existing-file candidates ∪ config pins (dedupe, discovery then pins). Keep or thin-wrap `default_db_path()` only if still needed by external callers after Step 5.

4. **Merge reader**
   - (a) Tests: disjoint IDs merge; shadowing regression; unreadable sibling skipped; cross-DB de-dupe; absent → `{}`.
   - (c) Add `load_enrichment()` (name OK to vary) that reads each resolved path via `read_enrichment` and merges with `_append_model`.

5. **Orchestrator seam**
   - (a) Orchestrator test: no `ai_tracking_db` kwarg / unset env; monkeypatch resolve/load to two synthetic DBs with disjoint ids matching fixture session ids → both get `sessions.models`. Existing `ai_tracking_db=` inject tests remain green (single-path override).
   - (c) `_ingest_cursor`: kwarg/env single path → one `read_enrichment`; else `load_enrichment()`. Update docstrings.

6. **Docs**
   - (a) Treat doc accuracy as the “test”: draft the intended paragraphs against AC4.
   - (c) Update `docs/user-guide/ingest.md` and `tests/fixtures/transcripts/README.md` if still first-hit. Optionally one line in `docs/user-guide/installed-layout.md` for `~/.config/stockroom/config.toml` (config home ≠ data home). No doctor/onboarding UI; no `state_vscdb`.

7. **Suite verify** — run targeted tests through the cycles above; full engine test suite before Build complete.

## Technology Validation

No new technology — validation not required. Uses stdlib `tomllib` (already used in engine tests) and existing `sqlite3` enrich path. XDG config home follows Freedesktop layout already used for data home in `stockroom.home`.

## Dependencies

- Aborted `enhance-cursor-tokens` only as discarded reference for `resolve_config_home` / `config.toml` fail-soft shape — not a merge source; no `state_vscdb`.
- Existing `_candidate_db_paths` / `_wsl_windows_candidate_paths` / `read_enrichment` / `_append_model`.
- Ingest apply seam (`if session_id in enrichment`) unchanged — walk/merge restores IDE keys so re-ingest stops wiping those models.

## Challenges & Mitigations

- **Accidental `state_vscdb` revival**: Settings/docs must only expose `ai_tracking_dbs`. Mitigation: explicit non-goal in tests/docstrings; do not copy aborted `Settings.cursor_state_vscdb`.
- **Path identity across mounts**: dedupe by normalized path strings (`expanduser`; `resolve` when exists). Mitigation: best-effort dedupe; duplicate reads are fail-soft waste.
- **Overlapping conversationIds across DBs (rare)**: first-seen wins via `_append_model`. Mitigation: match in-DB semantics.
- **Warehouse-outlives residual**: re-write with total enrich miss can still clear models. Mitigation: out of #82 acceptance; note in reflection if seen.
- **Doctor/onboarding**: issue left open; brief AC is docs. Mitigation: docs-only.

## Pre-Mortem

- **Plan fixed helpers but left orchestrator on `default_db_path()`**: dead API. Response: Step 5 + orchestrator multi-DB test mandatory.
- **Copied aborted config wholesale including `state_vscdb`**: scope creep. Response: Settings field list is the gate.
- **Config pins replace discovery**: recreates single-source failure. Response: union + additive pin tests.
- **Assumed XDG already on branch**: it is not. Response: Steps 1–2 create fresh.

## Preflight Amendments

- Encoded explicit **(a) failing tests → (b) confirm fail → (c) implement → (d) pass** on every implementation unit (TDD blocking fix).
- Added orchestrator-level default multi-DB → `sessions.models` behavior (closes AC1/AC3 gap if only unit tests shipped).
- Noted optional `installed-layout.md` mention of XDG config home (still no doctor UI).

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Pre-Mortem complete
- [x] Preflight
- [x] Build
- [x] QA
