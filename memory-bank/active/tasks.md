# Task: Workspace identity vs. real path (`project_id` + `cwd` recovery)

* Task ID: `p1-data-backbone-m4-cwd-recovery`
* Complexity: Level 2
* Type: enhancement (schema `0002` migration + ingest path-model fix)

Replace the lossy, fabricating `sessions.project_path` with two single-meaning columns: **`project_id`** (the harness's encoded project-dir slug, stored *verbatim* — the always-present grouping identity) and a re-semantic **`cwd`** (the real project-root path, best-effort, **NULL when unknown**). Drop the lossy `decode_project_dir`. Populate `cwd` by **re-encode-and-match** over in-band transcript paths for Cursor and the authoritative record `cwd` for Claude. Ship the schema change as a forward **`0002`** migration through the m2 framework (dogfooding the first real schema-changing, data-preserving upgrade), keeping `0001` and its golden snapshot frozen. Full design + evidence: `planning/spikes/cwd-recovery/README.md`.

## Locked Prerequisite — the `encode` transform (resolved in PLAN)

Empirically locked via `planning/spikes/cwd-recovery/probe_encode.py` against the operator's real history (78 Cursor + 6 Claude slugs):

- The slug alphabet is **exactly `[A-Za-z0-9-]`** — across all 84 real slugs the *only* non-alphanumeric character is `-`. No `_`, space, or other char ever survives.
- Claude `encode(record_cwd) == dirname` holds on every probeable case (0 mismatches); the double-dash in `…git--cursor-rules` confirms `.`→`-`.
- **Canonical transform:** `encode(p) = re.sub(r'[^A-Za-z0-9]', '-', p)` (every non-alphanumeric char → `-`). Per-harness leading-separator handling: **Cursor strips** the leading separator (slugs start with a letter, e.g. `home-…`); **Claude keeps** it (leading `/`→`-`, e.g. `-home-…`). Broader and safer than `[/.]`; since the failure mode is a clean NULL, residual imperfection can never fabricate a path.

## Test Plan (TDD)

### Behaviors to Verify

**`encode` / cwd resolver (`paths.py`)**
- `encode("/home/user/lite-rpg")` → `"home-user-lite-rpg"` (cursor, leading sep stripped); `encode_claude("/home/user/lite-rpg")` → `"-home-user-lite-rpg"`.
- `encode` collapses `.`, `_`, and other non-alphanumerics to `-` (e.g. `asuswrt-merlin.ng`-shaped path → all `-`).
- Cursor recovery (hyphen leaf): slug `home-user-lite-rpg` + transcript text containing `/home/user/lite-rpg` → `cwd == "/home/user/lite-rpg"` (NOT the naive `/home/user/lite/rpg`).
- Cursor recovery (dot leaf): slug + in-band path with a `.` leaf → recovers the dotted real path.
- Cursor ancestor walk: an in-band path *deeper* than the project root (`/home/user/lite-rpg/src/x.py`) → walks ancestors, returns the ancestor whose `encode == slug`.
- Cursor no evidence: slug `home-user-cursor-rules`, no in-band absolute path → `cwd is None` (honest NULL).
- Claude short-circuit: `record_cwd="/home/user/project"` → returned as-is, no matching needed.
- Deletion-proof / deterministic: resolver consults only the passed-in text/record_cwd — **never the live filesystem** (so the golden stays machine-independent).

**`0002` migration (`test_schema_0002.py`)**
- Data-preserving: seed a `0001`-shape `sessions` row (with `project_path`, `cwd`, + a message/tool_call), apply `0002` → the row and its children survive; `cwd` value intact.
- Column shape: after `0002`, `sessions` has `project_id` and no `project_path`; `cwd` unchanged.
- Cumulative schema matches a new golden `0002_snapshot.json` (mirrors the `0001` snapshot discipline; `0001_snapshot.json` stays untouched).

**`sources.py` discovery**
- `project_id` is the **verbatim** dir name (Cursor `home-user-project`, Claude `-home-user-project`) — no transform.
- `decode_project_dir` is gone (no remaining caller).

**`writer.py`**
- Inserts `project_id` (and `cwd`) into the post-`0002` `sessions` table; round-trips.

**Orchestrator (`__init__`) — integration over fixtures**
- Cursor session: `project_id` = verbatim slug; `cwd` recovered from in-band path or NULL; subagents inherit parent `project_id` + `cwd`.
- Claude session: `project_id` = verbatim slug; `cwd` = record cwd (authoritative); latent bug fixed (no lossy decode stamped).
- Golden `expected_rows.json` regenerated: every row carries `project_id` (not `project_path`) and the resolved/NULL `cwd`.
- **No-fabrication round-trip invariant (preflight radical-innovation, applied):** over the whole ingested corpus, every `sessions` row satisfies `cwd IS NULL OR encode_for(harness, cwd) == project_id`. A general property assertion (not per-fixture) that locks the core correctness claim — a populated `cwd` always re-encodes to its own slug, so a fabricated path is structurally impossible to store.

### Test Infrastructure

- Framework: `pytest`, configured in `skills/sr-search/pyproject.toml`; run via `make test` / `make ci`.
- Test location: `skills/sr-search/tests/`.
- Conventions: `test_*.py`, one module per unit; in-memory DuckDB; no `from __future__ import annotations`.
- **New fixture `migrated_con`** (conftest): in-memory DuckDB with the full chain applied via `migrate.apply_pending(con)` (real packaged `0001`+`0002`). Ingest **writer + orchestrator** tests move onto it; `schema_con` (0001-only) stays for the frozen `0001` contract tests.
- New test files: `test_ingest_paths.py`, `test_schema_0002.py`.
- New fixtures: a Cursor project `home-user-lite-rpg/agent-transcripts/recover-inband/recover-inband.jsonl` (in-band `/home/user/lite-rpg` → locks hyphen-leaf recovery) and `home-user-cursor-rules/agent-transcripts/ambiguous-nopath/ambiguous-nopath.jsonl` (no path → locks `cwd = NULL`). Update `tests/fixtures/transcripts/README.md`.

## Implementation Plan

Each step is one RED→GREEN TDD cycle (failing test(s) first, then implementation), one commit per step.

1. **`paths.py` resolver + `encode`** — RED: `test_ingest_paths.py` (encode transform per harness; cursor in-band recovery of hyphen/dot leaves + ancestor walk; NULL when no evidence; claude short-circuit; no-FS-access guard). GREEN: new `paths.py` with `encode`, harness-aware `encode_for`, and `resolve_cwd(harness, slug, *, record_cwd, texts)`.
   - Files: `src/stockroom/ingest/paths.py`, `tests/test_ingest_paths.py`.
2. **`model.py` field rename** — RED: update `test_ingest_model.py` to the `project_id` field. GREEN: rename `NormalizedSession.project_path` → `project_id` (+ docstring).
   - Files: `src/stockroom/ingest/model.py`, `tests/test_ingest_model.py`.
3. **`sources.py` verbatim `project_id`** — RED: `test_ingest_sources.py` — drop `test_decode_project_dir`; assert `DiscoveredSession.project_id` is the verbatim slug. GREEN: rename the field; stamp `project_id = project_dir.name`; delete `decode_project_dir`; refresh the docstring.
   - Files: `src/stockroom/ingest/sources.py`, `tests/test_ingest_sources.py`.
4. **`0002` migration + contract/snapshot + `migrated_con`** — RED: `test_schema_0002.py` (data-preserving; column added/dropped; cumulative `0002_snapshot.json` via the introspection helper). Add the `migrated_con` fixture. GREEN: author `migrations/0002_workspace_identity.sql` (`ALTER TABLE sessions ADD COLUMN project_id TEXT; ALTER TABLE sessions DROP COLUMN project_path;`); generate `0002_snapshot.json`.
   - Files: `src/stockroom/migrations/0002_workspace_identity.sql`, `tests/test_schema_0002.py`, `tests/fixtures/schema/0002_snapshot.json`, `tests/conftest.py`.
5. **`writer.py` writes `project_id`** — RED: `test_ingest_writer.py` on `migrated_con` asserts `project_id`/`cwd` persist. GREEN: swap `project_path`→`project_id` in the `sessions` INSERT column list + values.
   - Files: `src/stockroom/ingest/writer.py`, `tests/test_ingest_writer.py`.
6. **Fixtures for recovery + NULL** — RED: add the two Cursor fixtures + update `transcripts/README.md` and the discovery test's expected stem set. GREEN: fixtures are data (no code).
   - Files: `tests/fixtures/transcripts/cursor/**`, `tests/fixtures/transcripts/README.md`, `tests/test_ingest_sources.py`.
7. **Orchestrator: stamp `project_id` + resolve `cwd`** — RED: `test_ingest_orchestrator.py` on `migrated_con`; dump helper `project_path`→`project_id`; add cwd-recovery (non-NULL) + NULL assertions; regenerate `expected_rows.json` (`STOCKROOM_UPDATE_INGEST_GOLDEN=1`). GREEN: in `_parse_discovered`, stamp `project_id = discovered.project_id` for both harnesses; for Cursor set `cwd = paths.resolve_cwd("cursor", project_id, record_cwd=None, texts=<message texts + tool inputs>)` and have subagents inherit the parent's `project_id`+`cwd`; for Claude keep the record `cwd` and remove the lossy-decode stamping (latent-bug fix).
   - Files: `src/stockroom/ingest/__init__.py`, `tests/test_ingest_orchestrator.py`, `tests/fixtures/ingest/expected_rows.json`.
8. **Sweep + docs** — grep-sweep residual `project_path` / `decode_project_dir`; specifically refresh the now-stale parser docstrings `claude.py` (line ~274) and `cursor.py` (line ~26) that describe the old `project_path` decode, and confirm `__main__` carries no reference (verified at preflight: none). Update `techContext.md` Warehouse Schema note (project_id/cwd, the `0002` migration) and `tests/fixtures/transcripts/README.md`. Defer the durable `systemPatterns.md` cwd-recovery/re-encode-match pattern entry to REFLECT unless it firms up here.
   - Files: `src/stockroom/ingest/{claude,cursor}.py` (docstrings), `memory-bank/techContext.md`, fixtures README (+ `systemPatterns.md` if warranted).
9. **Green gate** — `make ci`: sync, `lock --locked` (uv.lock untouched), ruff lint + format-check, full `pytest`, `reuse lint` (path-based AGPL on new `*.py`/`*.sql`/fixtures — no inline SPDX).

## Technology Validation

**No new technology — validation not required.** Implementation uses stdlib `re`/`pathlib` and the already-locked `duckdb` + the m2 migration framework; `uv.lock` is untouched (`make lock-check` guards it). The single empirical prerequisite — the `encode` transform — was **resolved during PLAN** by `planning/spikes/cwd-recovery/probe_encode.py` (slug alphabet `[A-Za-z0-9-]`; Claude `encode(cwd)==slug` confirmed). DuckDB `ALTER TABLE ADD/DROP COLUMN` is standard and exercised by the m2 runner.

## Dependencies

- The m2 migration framework (`stockroom.migrate.apply_pending`, `stockroom.migrations.discover`) — applies `0002`.
- The m3 ingest pipeline (`sources`/`model`/`cursor`/`claude`/`writer`/orchestrator) — the surface being amended.
- The frozen `0001` schema + its golden snapshot — must remain untouched (forward-only invariant).

## Challenges & Mitigations

- **`schema_con` applies only `0001`; the writer now targets post-`0002`.** → New `migrated_con` fixture (full chain via `apply_pending`); move ingest writer/orchestrator tests onto it; keep `schema_con` for the frozen `0001` contract tests.
- **Golden-snapshot determinism.** → v1 resolver consults only in-band transcript text (Cursor) and the record `cwd` (Claude) — **never the live filesystem**; the optional FS-walk generator is explicitly out of scope, so the golden stays machine-independent.
- **`project_id` is not backfillable from the lossy `project_path`** (the slug was decoded away). → The `0002` migration is structural (NULL `project_id` for any pre-existing row); the operator's warehouse is rebuilt by a `--full` re-ingest (it is derived ETL output), and data-preservation is proven mechanically (rows/children/`cwd` survive the `ALTER`).
- **`0001` is frozen.** → Forward `0002` only; new `0002_snapshot.json`; `0001_initial_schema.sql` and `0001_snapshot.json` untouched.
- **`ADD COLUMN` appends `project_id` at the end** (physical order shifts). → Expected and captured by `0002_snapshot.json`.
- **L4-creep / re-level check.** → One cohesive change over the existing ingest + migration subsystem; no new architecture, no independent workstreams; design fully pre-resolved. Stays Level 2 (re-confirm at preflight).

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Preflight — PASS (no blocking findings; round-trip no-fabrication invariant added; parser-docstring sweep named)
- [ ] Build
- [ ] QA
