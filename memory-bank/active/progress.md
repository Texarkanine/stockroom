# Progress

Milestone 1 of the `p1-data-backbone` L4 project: **Schema field enumeration + locked DDL**. Point an agent at real Cursor and Claude Code transcripts side by side, enumerate every field each format exposes, then lock one shared, harness-labeled set of tables (sessions, messages, tool calls inputs-only, plan documents, embeddings, sync-state watermark) encoding the stable message-identity contract and the conversation-reconstruction keys. Authored test-first against real and pathological fixtures, with the DDL written directly as the `0001` migration file and the enumeration evidence + shared fixtures committed as durable artifacts.

**Complexity:** Level 3

## 2026-06-24 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - Re-entered `/niko` on the `p1-data-backbone` L4 project in the "Not started" state (milestones.md present, no sub-run yet classified).
    - Classified the first unchecked milestone (Schema field enumeration + locked DDL) as **Level 3**, matching the L4 plan/preflight advisory estimate.
    - Created sub-run ephemeral files (this `progress.md`, stubbed `tasks.md`, refreshed `activeContext.md`); preserved the L4 `projectbrief.md` and `milestones.md`.
* Decisions made
    - L3, not L4: a complete feature across multiple cooperating components (two-format empirical enumeration, multi-table contract authored as migration `0001`), but the architecture is already fixed by the L4 plan — this sub-run produces one cohesive artifact set, not new subsystems.
* Insights
    - Operator override in effect: regardless of level, once the initial schema is drafted, STOP for operator review of (a) every field that exists in both harnesses and (b) the recommended kept subset. This maps to the L3 Plan → Creative path, where the schema is the open question and a draft pending sign-off is a legitimate "stop for operator" creative outcome.

## 2026-06-24 - PLAN/CREATIVE (schema enumeration) - STOPPED FOR REVIEW

* Work completed
    - Located on-disk data for both harnesses and ran a key-path enumerator over the full corpus (Cursor: 713 files / 25,065 records; Claude: 39 files / 4,158 records). Raw evidence committed under `memory-bank/active/creative/evidence/`.
    - Authored `creative/creative-schema-enumeration.md`: complete two-harness field enumeration with per-field KEEP/DERIVE/ENRICH/DROP dispositions, the subagent-linkage + message-identity analysis, an illustrative 6-table schema sketch, and 6 open questions.
* Decisions made (provisional, pending operator sign-off)
    - Stored content is tool **inputs only**; Claude `tool_result`/`toolUseResult` and all token-usage subtrees are DROP (token/cost is a v1 exclusion).
    - Cursor has no native ids/parent/model/timestamp → the message-identity contract mints deterministic surrogates for Cursor and adopts native `uuid`/`parentUuid` for Claude; `model`/`ts` are NULLable (enriched at ingest).
    - Subagent↔parent is field-based for Claude (`agentId` + `meta.json.toolUseId`) but structural-only for Cursor (`subagents/` containment).
* Insights
    - The two on-disk formats are radically asymmetric: Claude is self-describing; Cursor's transcript is a bare `role`/`message` list. The shared harness-labeled schema absorbs this by making Claude-native columns nullable/synthesized for Cursor.
    - `plan_documents` has no distinct on-disk record in either harness — its populating source is the weakest-grounded part of the brief's table list (open question Q3).
    - DDL deliberately NOT locked; awaiting operator review before authoring `migrations/0001` test-first.

## 2026-06-24 - PREFLIGHT - PASS (with advisories)

* Work completed
    - Validated the plan against codebase reality (TDD encoding, conventions, dependency impact, conflicts, completeness). Wrote `memory-bank/active/.preflight-status`.
    - Confirmed `REUSE.toml` is **path-based**: `skills/**/*.sql` + `skills/**/tests/**` already assert AGPL (covers the migration SQL and `.jsonl`/snapshot fixtures) — no inline SPDX headers needed. Confirmed no pre-existing `.sql`/migration code (no conflict).
* Amendments made to `tasks.md`
    - Hardened per-unit test-first ordering in implementation steps 3–8 (TDD-encoding check).
    - Corrected the licensing step (path-based REUSE; dropped the wrong "add SPDX headers" instruction).
    - **Radical-innovation finding (in-scope, applied):** added a golden **locked-schema snapshot** test (introspect `duckdb_columns`/`duckdb_constraints` → compare to committed `0001_snapshot.json`) — makes "locked DDL" literally enforced and gives m2 a regression guard.
* Advisory (non-blocking)
    - `plan_documents` dropped vs the Project Brief's named table list — operator-approved in creative, documented; recorded for visibility.
* Next
    - 🧑‍💻 Operator-gated **Build** (`/niko-build`). Preflight PASS → Build requires operator initiation per the L3 workflow.

## 2026-06-24 - PLAN - COMPLETE

* Work completed
    - Wrote the full L3 implementation plan to `tasks.md` (component analysis, TDD behaviors, 10 ordered implementation cycles, challenges, status).
    - Grounded the plan in the real repo layout: engine `skills/sr-search/`, pkg `src/stockroom/`, pytest with `pythonpath=["src"]` + `repo_root` fixture; DDL lands at `src/stockroom/migrations/0001_initial_schema.sql` (m2 wraps it in place).
    - Ran the Technology-Validation POC: representative DDL on DuckDB 1.5.4 — `VARCHAR[]`/`JSON`/`FLOAT[384]`/composite-PK parse; reconstruction, `json_extract`, `list_contains`, token `SUM`, subagent self-link all correct; dup PK → `ConstraintException`.
* Decisions made (in-plan, no creative needed)
    - No DB-level FK constraints in `0001` (DuckDB FK limits + ETL ordering); enforce logically in m3, assert via reconstruction tests.
    - No `CHECK` on `harness` (future-harness extensibility).
    - `embeddings` table defined without the HNSW index (VSS is Phase 2).
    - Schema-apply is test-only (`schema_con` fixture); no migration runner (that is m2).
* Insights
    - The only product artifact is one `.sql` file; everything else is tests + durable fixtures. Tight, low-blast-radius milestone despite being the highest-leverage contract.
    - No new dependency — duckdb already locked, POC green, so Technology Validation is satisfied.

## 2026-06-24 - CREATIVE - COMPLETE (operator review resolved, high confidence)

* Work completed
    - Operator review of `creative/creative-schema-enumeration.md` completed across several rounds; **all open questions resolved**, doc status flipped to REVIEWED/ready-to-lock.
    - Added a Mermaid ERD + an explicit "how reconstruction works" model; verified empirically that text never follows a tool within a turn (0/5,646), so concatenated-text + ordered-tool-children is lossless.
    - Canonized three durable principles in `systemPatterns.md`: one-meaning-per-field (cross-harness semantic uniformity), typed-columns-not-JSON-blobs (DuckDB has no JSON-path index), and thinking-not-captured.
* Decisions made (operator-confirmed, now binding for the DDL)
    - **Schema is FIVE tables** — `plan_documents` dropped (no on-disk source; `TodoWrite` lives in `tool_calls.tool_input`).
    - **Identity is uniform**: `message_id = {session_id}#{ordinal}` for both harnesses (deterministic surrogate); native ids demoted to `source_uuid`/`source_tool_use_id` provenance (never joined). `ordinal` = position-in-session, one meaning across harnesses. Stability rests on the append-only-log invariant, with `_sync_state` size/mtime detection of rewrites.
    - **Dropped**: `is_meta`, `caller_type`, `thinking` (separable→dropped), the non-cost `usage` extras.
    - **Token usage KEPT as four typed `BIGINT` columns** on `messages` (input/output/cache_creation/cache_read), not a JSON blob.
    - **Model split by grain, no faking**: `messages.model` (Claude, per-message) + `sessions.models VARCHAR[]` (Cursor, per-conversation); each harness fills only the grain it has.
    - **Cursor CLI `store.db` deferred out of v1**: investigated — a content-addressed blob DAG (mixed JSON+protobuf) embedding tool outputs + reasoning; needs its own ingestion adapter/milestone.
    - **`ai-code-tracking.db` enrichment** limited to `model` (→ `sessions.models`) + session-time refinement; attribution/file tables dropped.
* Insights
    - The hard design forces were cross-harness *meaning* uniformity and ID *stability* — both now have explicit, defensible answers backed by data, not assertion.
    - Next: PLAN the test-first build of `migrations/0001` (DDL) + fixtures.

## 2026-06-24 - BUILD - COMPLETE

* Work completed
    - Executed all 11 implementation steps test-first. Authored the locked five-table DDL `skills/sr-search/src/stockroom/migrations/0001_initial_schema.sql` (+ `migrations/__init__.py`) and the `schema_con`/`schema_sql_path` fixtures (read+execute DDL on in-memory DuckDB; located via `stockroom.__file__`; no migration runner — that is m2).
    - Wrote 46 schema-contract tests in `tests/test_schema_0001.py`: structure, composite-PK uniqueness, NOT NULL, reconstruction/threading/subagent linkage, model-grain no-faking, typed-token aggregation, JSON path extraction, native LIST, no-truncation round-trip, fixed-size FLOAT[384], harness-neutrality, pathological cases, and a golden locked-schema snapshot vs committed `tests/fixtures/schema/0001_snapshot.json`.
    - Curated durable native-format transcript fixtures (`tests/fixtures/transcripts/{cursor,claude}/` + README): scrubbed real-shaped samples + crafted pathological cases. Artifacts for m3; not parsed by m1 tests.
    - Added a `techContext.md` pointer to the migration SQL, snapshot, and fixtures.
    - `make ci` green: 63 passed (46 new + 17 existing); ruff lint+format clean; lock verified; REUSE 117/117 compliant.
* Decisions made
    - Step 2 deferred non-PK NOT NULLs to step 3's test-first cycle; all required NOT NULLs landed RED→GREEN.
    - Snapshot introspection filters `duckdb_columns()` to `internal = false` (DuckDB surfaces system catalog tables in `main`).
    - Transcript fixtures are scrubbed/synthetic-content but real-shape — no real transcript bytes committed (secrets/PII safety), documented in the fixtures README.
* Insights
    - The schema supported every reconstruction/threading/grain/fidelity behavior with no DDL change beyond the planned columns + constraints — the empirical enumeration held up.
    - The golden snapshot makes "locked DDL" literal and hands m2 a ready-made regression guard.

## 2026-06-24 - QA - PASS

* Work completed
    - Semantic review of the build against the plan (KISS/DRY/YAGNI/completeness/regression/integrity/documentation). Verified the DDL matches creative §4 column-for-column, all 11 steps + every test-plan behavior are implemented, conventions hold, and docs are updated. Wrote `memory-bank/active/.qa-validation-status`.
    - Applied one trivial fix in `test_composite_pk_rejects_duplicate`: removed an unused `pk_cols` parametrize argument and made the second insert vary a non-PK column, so the test proves PK-only collision (matching its docstring) rather than carrying a dead param + misleading comment.
    - Re-ran `make ci`: green — 63 passed, lint/format clean, lock verified, REUSE 117/117.
* Decisions made
    - PASS (clean; the single finding was trivial and fixed in-phase, no route-back).
* Insights
    - The only semantic debris was a parametrized test argument that drifted from its body — caught precisely because QA reads intent, not just green checks.

## 2026-06-24 - REFLECT - COMPLETE

* Work completed
    - Reviewed the full plan→creative→preflight→build→QA lifecycle; wrote `reflection/reflection-p1-data-backbone-m1-schema-ddl.md`.
    - Reconciled persistent files: no changes needed (systemPatterns schema principles + techContext schema pointer already accurate; productContext unaffected).
* Decisions made
    - Milestone 1 is complete and verified; reflection is terminal for this sub-run. Next is operator-initiated `/niko` to advance the L4 project.
* Insights
    - Technical: DuckDB `duckdb_columns()` surfaces internal catalog tables in `main` — introspection must filter `internal = false`; a golden snapshot generated via the test's own introspection function is a self-consistent, high-leverage DDL lock; JSON array length needs `json_array_length`, not `len()`.
    - Process: a planning-time POC against the real engine version is the highest-ROI step for a data-contract task; parametrized tests are a quiet home for unused-argument debris — verify every param is consumed.

## 2026-06-24 - PLAN/CREATIVE (correction) - Cursor side-store enumerated

* Work completed
    - Operator flagged that the Cursor enumeration undersold the data. Located `ai-code-tracking.db` on the Windows mount (`/mnt/s/Users/Austin/.cursor/ai-tracking/`), enumerated all 6 tables (evidence: `creative/evidence/cursor-ai-code-tracking-db.txt`), and verified against the live `cursor-warehouse.duckdb` via `/cw-query`.
    - Reviewed `cursor-warehouse/scripts/sync.py` under operator direction (sourcing only, not schema lift); revised `creative-schema-enumeration.md` §1a/§1b/§2/§3a and the open questions.
* Decisions made (provisional)
    - Cursor `model` IS recoverable — conversation-grained via `ai_code_hashes.conversationId` join (~86% of messages, 18 models), only for code-producing conversations. Per-message timestamps remain NULL; session times from file mtime, refinable from `ai_code_hashes.timestamp`.
    - `ai-code-tracking.db` enrichment recommended limited to `model` (+ session-time refinement); `scored_commits`/`ai_deleted_files`/`tracked_file_content` map to roadmap v1 exclusions → DROP. `conversation_summaries` is empty → no Cursor title today.
* Insights
    - cursor-warehouse independently mints `{session_id}:{line_idx}` ids, nulls message timestamps, and derives subagent parents structurally — strong corroboration of the empirical contract.
    - "model-per-chain" is genuinely asymmetric: true per-message for Claude, conversation-grained for Cursor.
    - Process note: an earlier `cp` used relative paths under a `/tmp` cwd, so the first evidence files never entered the repo; re-created with absolute paths.
