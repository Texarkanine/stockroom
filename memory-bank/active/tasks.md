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
- **Regression**: existing single-DB `read_enrichment` schema/order/malformed behaviors unchanged.
- **Docs**: ingest user-guide describes multi-DB merge, additive `ai_tracking_dbs`, and env single-DB override semantics.

### Test Infrastructure

- Framework: pytest (+ pytest-xdist) under `skills/sr-search/`
- Test location: `skills/sr-search/tests/`
- Conventions: `test_*.py`; enrich path tests monkeypatch `Path.home` / `_wsl_windows_candidate_paths` / env; synthetic sqlite DBs via `tmp_path` + `sqlite3` (see `test_ingest_enrich.py` / `ai_tracking_db` fixture)
- New test files: `tests/test_config.py` (XDG settings); extend `tests/test_ingest_enrich.py` (and small home tests if `resolve_config_home` lands in `home.py`). Optional thin orchestrator case only if merge seam is not fully covered at enrich layer — prefer enrich-unit coverage.

## Implementation Plan

1. **XDG config home (stdlib)** — add `resolve_config_home()` (+ source labels) to `skills/sr-search/src/stockroom/home.py` (pattern from aborted branch; no mkdir). Tests in new `tests/test_config.py` (or `test_home_config.py` if preferred) for XDG env vs `~/.config/stockroom` default and purity.
2. **Fresh `stockroom.config`** — new `skills/sr-search/src/stockroom/config.py`: `Settings` with `cursor_ai_tracking_dbs: tuple[Path, ...] = ()` only; `load_settings()` reads `$XDG_CONFIG_HOME/stockroom/config.toml` via `tomllib`, fail-soft. **Do not** add `state_vscdb`. Tests: missing/malformed/empty; valid list of strings → Paths; ignore non-string / empty entries.
3. **Resolve path set** — in `enrich.py`: add `resolve_db_paths()` (name may vary) = env override → single path; else existing existing-file candidates from `_candidate_db_paths()` ∪ config pins, deduped, stable order (discovery then pins). Retarget/replace first-hit tests; keep `default_db_path()` as thin helper (first resolved existing path, else modern conventional) only if still useful for callers/docs — or deprecate if unused after orchestrator switch.
4. **Merge reader** — add `load_enrichment()` (or `read_enrichment_many`) that `read_enrichment`s each path fail-soft and merges into one `{conversation_id: [models…]}` using existing `_append_model` first-seen order. Tests: disjoint merge, shadowing regression, unreadable sibling skip.
5. **Orchestrator seam** — `_ingest_cursor` in `ingest/__init__.py`: when `ai_tracking_db` is set, read that one path; else `load_enrichment()` / resolve+merge. Update docstrings. Existing inject tests keep passing.
6. **Docs** — update `docs/user-guide/ingest.md` (and `tests/fixtures/transcripts/README.md` if it still describes first-hit). Mention multi-DB merge, `~/.config/stockroom/config.toml` `[cursor].ai_tracking_dbs`, and that `STOCKROOM_AI_TRACKING_DB` forces a single DB. No doctor/onboarding UI work; no `state_vscdb` docs.
7. **Verify** — run enrich/config tests during TDD; full `make test` (or project equivalent) before claiming build done.

## Technology Validation

No new technology — validation not required. Uses stdlib `tomllib` (already used in engine tests) and existing `sqlite3` enrich path. XDG config home follows Freedesktop layout already used for data home in `stockroom.home`.

## Dependencies

- Aborted `enhance-cursor-tokens` only as discarded reference for `resolve_config_home` / `config.toml` fail-soft shape — not a merge source; no `state_vscdb`.
- Existing `_candidate_db_paths` / `_wsl_windows_candidate_paths` / `read_enrichment` / `_append_model`.
- Ingest apply seam (`if session_id in enrichment`) unchanged — walk/merge restores IDE keys so re-ingest stops wiping those models.

## Challenges & Mitigations

- **Accidental `state_vscdb` revival**: Settings/docs must only expose `ai_tracking_dbs`. Mitigation: explicit non-goal in tests/docstrings; do not copy aborted `Settings.cursor_state_vscdb`.
- **Path identity across mounts**: dedupe by `Path` string as resolved in config/discovery (normalize via `expanduser` + resolve when path exists). Mitigation: document best-effort dedupe; duplicate reads are fail-soft waste, not correctness bugs.
- **Overlapping conversationIds across DBs (rare)**: first-seen wins via `_append_model`. Mitigation: match in-DB semantics; no special conflict policy.
- **Warehouse-outlives residual**: if a session is re-written and missing from *all* tracking DBs, models can still clear. Mitigation: out of acceptance for #82 (fix is shadowing); note in reflection if observed — do not expand scope to "preserve prior models on enrich miss" unless operator reopens.
- **Doctor/onboarding**: issue left open; brief AC is docs. Mitigation: docs-only; no initialize prompts.

## Pre-Mortem

- **Plan "fixed" path resolution but left orchestrator on `default_db_path()`**: would ship dead API. Response: Step 5 is mandatory; acceptance tests must exercise default (no env) multi-path load, not only helpers.
- **Copied aborted config wholesale including `state_vscdb`**: product confusion and scope creep. Response: already constrained in Challenges; Settings field list is the gate.
- **Treated config pins as replacement for discovery**: recreates single-source failure mode for odd mounts. Response: resolution set is union; tests assert additive pins.
- **Assumed XDG already landed on this branch**: it has not — `home.py` has no config home yet. Response: Steps 1–2 create it fresh (covered).

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Pre-Mortem complete
- [ ] Preflight
- [ ] Build
- [ ] QA
