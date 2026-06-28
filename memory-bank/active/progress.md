# Progress

Milestone 4 of the `p1-data-backbone` L4 project: **Workspace identity vs. real path (`project_id` + `cwd` recovery)**. Fix the ingest path model surfaced post-m3: the encoded project-dir slug is lossily decoded into a *fabricated* path. Split `sessions` into `project_id` (verbatim slug — the always-present grouping identity, replacing `project_path`) and a best-effort, NULL-when-unknown `cwd` (the real project-root path) — populated by re-encode-and-match over in-band transcript paths for Cursor and the authoritative record `cwd` for Claude. Drop the lossy `decode_project_dir`; ship as a forward `0002` migration through the already-built m2 framework. Full design + evidence in `planning/spikes/cwd-recovery/README.md`. Preserves the L4 cross-milestone invariants (forward-only numbered migrations, harness-labeled single schema, one-meaning-per-column / honestly-NULL, no fabrication, golden-snapshot regression guard, green `make ci`).

**Complexity:** Level 2

## 2026-06-28 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - Re-entered `/niko` on the `p1-data-backbone` L4 project. Milestone 3 (Trace ingest / ETL) was `REFLECT - COMPLETE`; checked it off in `milestones.md` and cleared its sub-run ephemeral files per Step 2a (`tasks.md`, `activeContext.md`, `progress.md`, `creative/`, `.qa-validation-status`, `.preflight-status`). Preserved `milestones.md`, the L4 `projectbrief.md`, and prior `reflection/` docs.
    - Verified the ephemeral creative doc `creative-cursor-workspace-path-recovery.md` was safe to reap: its full design is durably preserved in `planning/spikes/cwd-recovery/README.md` (which explicitly supersedes it and is referenced by the milestone-4 line).
    - Classified the next unchecked milestone (Workspace identity vs. real path) as **Level 2**, matching the L4 plan/spike estimate.
    - Created fresh sub-run ephemeral files (this `progress.md`, stubbed `tasks.md`, refreshed `activeContext.md`).
* Decisions made
    - **L2, not L3:** a cohesive data-model refinement over already-built infrastructure (m2 migration framework + m3 ingest), not a new architecture. Design is fully pre-resolved in the spike (data model, `cwd` algorithm, and the `0002`-migration route all decided), so no creative phase is needed; the lone open item is an empirical confirmation of the `encode` transform's escaped-character set, handled as the plan's first step. The "flag L3 if the resolver + dual-snapshot churn proves broad" condition is not triggered — one focused `cwd` resolver plus a standard forward migration and snapshot regen.
* Insights
    - This milestone *dogfoods* the m2 migration framework on its first real schema-changing, data-preserving upgrade (`ALTER TABLE` + backfill) — exactly the Phase-1 "Done When" proof — at low risk (the warehouse is derived ETL output, rebuildable via `--full`).
    - Correctness is cheap by construction: `project_id` is copied verbatim (can't be wrong) and `cwd` is verified by forward-encoding (`encode(candidate) == slug`), so its only failure mode is a clean NULL — never a fabricated path.

## 2026-06-28 - PLAN - COMPLETE (no creative phase)

* Work completed
    - Surveyed the full surface to be amended: ingest (`sources`/`model`/`cursor`/`claude`/`writer`/orchestrator), the m2 migration framework (`migrate`/`migrations`/`warehouse`), the frozen `0001` schema + its golden snapshot, and the test infra (`conftest` fixtures, `test_schema_0001`, `test_ingest_*`, golden `expected_rows.json`, fixture transcript layout).
    - Wrote the L2 plan to `tasks.md`: 8 behavior groups, a 9-step ordered TDD plan (new `paths.py` resolver → `model`/`sources` rename → `0002` migration + `migrated_con` fixture + `0002_snapshot.json` → `writer` → recovery fixtures → orchestrator + golden regen → sweep/docs → green gate), challenges/mitigations, and technology validation.
    - **Resolved the lone prerequisite during PLAN** with a structural-only probe (`planning/spikes/cwd-recovery/probe_encode.py`) over the operator's real 78 Cursor + 6 Claude slugs.
* Decisions made
    - **Canonical `encode`**: `re.sub(r'[^A-Za-z0-9]', '-', p)` (every non-alphanumeric → `-`), Cursor strips the leading separator, Claude keeps it. Evidence: the real slug alphabet is exactly `[A-Za-z0-9-]`; broader/safer than `[/.]`, and the failure mode is a clean NULL so it can never fabricate.
    - **Test infra**: add a `migrated_con` fixture (full `0001`+`0002` chain via `apply_pending`) and move ingest writer/orchestrator tests onto it; keep `schema_con` (0001-only) for the frozen `0001` contract tests.
    - **`0002` is structural** (drop `project_path`, add `project_id`); no backfill (the slug isn't recoverable from the lossy decode) — re-ingest repopulates, and data-preservation is proven mechanically. `0001` + its snapshot stay frozen.
    - **v1 `cwd` resolver is deterministic**: Claude record `cwd` + Cursor in-band-path re-encode-match only; no live-FS walk (keeps the golden machine-independent and honors the survive-deletion invariant).
* Insights
    - The structural probe (the project's recurring highest-leverage planning act) turned the one open unknown into a locked, evidence-backed rule and even tightened it (`[/.]` → all non-alphanumerics) — a strictly safer transform discovered only by looking at real data.

## 2026-06-28 - PREFLIGHT - PASS

* Work completed
    - Validated the plan against codebase reality (TDD per-unit encoding, convention compliance, dependency impact, conflict detection, completeness). Wrote `.preflight-status`.
    - Swept `project_path`/`decode_project_dir` across the engine: every consumer is accounted for by the plan (orchestrator/writer/sources/model + the three ingest tests + golden). The only additions are two stale parser **docstrings** (`claude.py`, `cursor.py`) — folded into the step-8 sweep; the CLI has no reference; `0001` SQL + snapshot correctly stay frozen.
    - Confirmed the `schema_con` (0001-only) → `migrated_con` (0001+0002) fixture split is necessary and planned.
    - **L4-creep check: PASS** — one cohesive change over the existing ingest + migration subsystem; stays Level 2.
* Amendments made to `tasks.md`
    - **Radical-innovation (in-scope, applied):** a no-fabrication round-trip invariant in the orchestrator test — `cwd IS NULL OR encode_for(harness, cwd) == project_id` over the whole corpus — generally locks "a populated cwd always re-encodes to its slug."
    - Named the two parser docstrings explicitly in the step-8 sweep.
* Advisories (non-blocking)
    - Cursor `cwd` coverage is intentionally partial (NULL when no in-band path); 4/6 real Claude projects also lack a top-level record `cwd` → NULL. Data reality, not a defect.
    - Durable `systemPatterns.md` cwd-recovery pattern entry deferred to REFLECT.
* Next
    - PREFLIGHT PASS → BUILD is autonomous (solid edge) in the L2 workflow. Proceed to `/niko-build`.

## 2026-06-28 - BUILD - COMPLETE

* Work completed (TDD, RED→GREEN throughout; final `make ci` green: 168 passed, ruff clean, `uv.lock` locked, REUSE 152/152)
    - **`paths.py`** resolver + `test_ingest_paths.py` (committed as the first step): `encode`, harness-aware `encode_for`, `resolve_cwd(harness, slug, *, record_cwd, texts)` (in-band absolute-path regex + ancestor walk; FS-free).
    - **`0002_workspace_identity.sql`** (`ALTER TABLE sessions ADD COLUMN project_id TEXT; DROP COLUMN project_path`), `test_schema_0002.py` (data-preserving + column shape + cumulative golden), `0002_snapshot.json`, and the `migrated_con` fixture.
    - **Atomic source rename** `model`/`sources`/`writer`/orchestrator: verbatim `project_id = project_dir.name`; Cursor `cwd = resolve_cwd("cursor", slug, texts=<message text + tool inputs>)`; Claude keeps the authoritative record `cwd`; subagents inherit parent `project_id`+`cwd`; deleted `decode_project_dir`; refreshed `cursor.py`/`claude.py` docstrings.
    - **Fixtures + golden:** `recover-inband` (hyphen-leaf `/home/user/lite-rpg` recovery) and `ambiguous-nopath` (honest NULL); regenerated `expected_rows.json`; updated transcripts README + `techContext.md`.
    - **Framework tests** moved to head version 2 (migrate_runner, migrations_discovery, warehouse_open, warehouse_concurrency).
* Decisions made
    - **Single atomic commit, not per-step** (see surprise below): every intermediate commit must stay green, and the `0002`↔writer-rename coupling made the planned per-step boundaries non-green. Approach and TDD discipline unchanged.
    - **Existing Cursor sessions resolve `cwd = NULL`**: their fixtures use only relative paths, so nothing re-encodes to the slug — the honest, correct outcome (the round-trip invariant holds vacuously for NULL).
* Surprise (recoverable)
    - Adding `0002` advanced the migration head to v2, breaking framework tests that assumed "only 0001 / version 1" **and** the CLI integration tests (real warehouse at v2 + un-renamed writer → `project_path` BinderError). Preflight's dependency sweep enumerated `project_path` consumers but not migration-count/version assumptions. Diagnosed as recoverable (mechanical "a second migration now exists" updates + the already-planned rename), so folded into one green change. → REFLECT note.
* Insights
    - The no-fabrication round-trip invariant (`encode_for(harness, cwd) == project_id` for every non-NULL `cwd`) now holds corpus-wide as a general property test — the structural guarantee that a fabricated path cannot be stored.
    - `0002` is the first real schema-changing, data-preserving migration through the m2 framework — the Phase-1 "Done When" proof, dogfooded.
* Next
    - QA (`/niko-qa`) gates REFLECT for L2.
