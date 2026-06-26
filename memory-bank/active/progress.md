# Progress

Milestone 3 of the `p1-data-backbone` L4 project: **Trace ingest (ETL)**. Build the incremental, per-source watermarked extract-transform-load that fills the migrated DuckDB warehouse from the operator's own history. Both harnesses: Cursor and Claude Code (Claude Code parsed clean-room from its native on-disk format). Watermarked per source (`last_mtime` / `last_path`) with a `--full` reset; subagents included and linked to their parent; kept content stored untruncated; tool inputs only (no outputs, no raw layer); WSL/Windows-mount-aware path resolution; optional model/labeling enrichment from Cursor's `ai-code-tracking.db` limited to model/labeling fields. Written test-first against real and pathological fixtures, through the milestone-2 `warehouse.open()` chokepoint and the milestone-1 locked schema, preserving the L4 cross-milestone invariants (no truncation at rest, harness-labeled single schema, tool-inputs-only, forward-only migrations, harness-neutral `~/.stockroom/` warehouse home, locked-uv trust, green `make ci` gate).

**Complexity:** Level 3

## 2026-06-25 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - Re-entered `/niko` on the `p1-data-backbone` L4 project. Milestone 2 (Migration framework) was `REFLECT - COMPLETE`; checked it off in `milestones.md` and cleared its sub-run ephemeral files (`tasks.md`, `activeContext.md`, `progress.md`, `creative/`, `.qa-validation-status`, `.preflight-status`) per Step 2a.
    - Classified the next unchecked milestone (Trace ingest / ETL) as **Level 3**, matching the L4 plan/preflight advisory estimate.
    - Created fresh sub-run ephemeral files (this `progress.md`, stubbed `tasks.md`, refreshed `activeContext.md`); preserved the L4 `projectbrief.md`, `milestones.md`, and prior `reflection/` docs.
* Decisions made
    - L3, not L4: a complete feature across multiple cooperating components (two clean-room parsers, watermark state, WSL/mount-aware path resolution, subagent→parent linkage, optional enrichment) — but the overarching architecture is already fixed by the L4 plan and the now-built schema (m1) + migration framework (m2). This sub-run fills the existing warehouse through the existing `open()` chokepoint; it introduces no new architecture.
* Insights
    - The hard correctness claims (faithful untruncated capture, subagent linkage, harness generality) are exactly what the milestone says must be proven test-first against *real and pathological* fixtures — fixtures milestone 1 was tasked to commit as durable artifacts and that this milestone's ingest tests reuse.

## 2026-06-25 - PLAN - COMPLETE (no creative phase)

* Work completed
    - Wrote the full L3 plan to `tasks.md`: new `stockroom.ingest` package decomposition (`model`, `cursor`, `claude`, `sources`, `enrich`, `writer`, orchestrator `__init__`, `__main__` CLI), pinned ETL pipeline + source→schema mapping + identity/reconstruction-algorithm diagrams, TDD test plan (7 new test modules + fixture extensions), 11-step ordered implementation plan, technology validation (no new deps), and challenges/mitigations.
    - Surveyed the engine (m1 schema `0001`, m2 `warehouse`/`migrate`/`migrations`, conftest fixtures, pyproject/Makefile/REUSE) and the planning authorities (roadmap Phase 1, tech-brief Faithful-Capture/Ingest/Migrations/Storage-Concurrency).
    - Ran **structural-only** probes (no transcript content) of the operator's real Cursor + Claude logs to resolve the one genuinely ambiguous design point empirically.
* Decisions made (in-plan; the L4-plan/preflight "rest is standard ETL" prediction held — no creative needed)
    - **Reconstruction:** dense 0-based ordinals over *kept* messages; `message_id = {session_id}#{ordinal}`. Cursor parent = previous-kept (linear append); Claude parent = follow `parentUuid` tree to the nearest *kept* ancestor (native `uuid` demoted to `source_uuid`).
    - **Drops:** Claude `thinking`, `tool_result`/`toolUseResult` (outputs), and Cursor `turn_ended` are consumed but never stored (no schema column for turn_ended → not persisted in v1).
    - **Subagents:** Claude subagent `session_id` = subagent file stem (records carry the *parent's* `sessionId`); `parent_session_id`/`agent_id`/`agent_type`/`spawning_tool_use_id` from records + meta.json. Cursor subagent linked structurally by `subagents/` dir location.
    - **Incremental:** `_sync_state` per `(harness, source_root=scanned root)`; select `mtime > last_mtime` (tie-break `path > last_path`); idempotent delete-then-insert per `(harness, session_id)`; `--full` bypasses the watermark.
    - **No boundary risk:** no schema change / no new migration; stdlib `json`/`sqlite3` + locked `duckdb` only (`uv.lock` untouched). New env conventions `STOCKROOM_CURSOR_ROOT`/`STOCKROOM_CLAUDE_ROOT` (flag at preflight, as m2 did for `STOCKROOM_HOME`).
* Insights
    - The structural probe was the highest-leverage planning act (mirrors m1/m2's pre-build POCs): it converted "how do I reconstruct the thread?" from a guess into an evidence-backed decision (branching is real and common → the uuid tree is mandatory) and exposed that the committed fixtures **undercount** real Claude record-type diversity — a concrete, build-shaping risk that a fixtures-only plan would have missed.

## 2026-06-25 - PREFLIGHT - PASS (with advisories)

* Work completed
    - Validated the plan against codebase reality (TDD per-unit encoding, convention compliance, dependency impact, conflict detection, completeness). Wrote `.preflight-status`.
    - Confirmed no existing ingest code (grep hits were docstring/comment/README mentions only — no conflict/duplication), and that `test_packaging.py` asserts manifests/versions, not package contents, so a new `stockroom.ingest` subpackage cannot break it.
    - Confirmed REUSE is path-based (`skills/**/*.py` + `skills/**/tests/**` re-asserted AGPL) → no inline SPDX for the new modules, fixtures (`.jsonl`/`.json`/synthetic `.db`), or tests.
    - **L4-creep check: PASS** — one cohesive ETL subsystem, no independent workstreams, no new architecture; stays Level 3.
* Amendments made to `tasks.md`
    - **Radical-innovation (in-scope, applied):** added a **golden ingest-output snapshot** (`tests/fixtures/ingest/expected_rows.json`) asserted in impl step 8 and generated by the test's own query helper — locks the full reconstruction output (ordinals, parent_ids, drops, tokens, subagent edges). Mirrors m1's `0001_snapshot.json` and m2's snapshot guard.
* Advisories (non-blocking)
    - New env conventions `STOCKROOM_CURSOR_ROOT`/`STOCKROOM_CLAUDE_ROOT` (as m2 did with `STOCKROOM_HOME`).
    - m1 fixtures undercount real Claude record-type diversity → m3 extends fixtures + adds an "ignore unknown types" robustness test (doesn't re-open m1).
    - `ai-code-tracking.db` absent on this machine → enrichment happy-path tested via synthetic sqlite fixture; real-data validation deferred.
    - Durable `systemPatterns.md` ETL/clean-room-parser entry deferred to reflect.
* Next
    - 🧑‍💻 Operator-gated **Build** (`/niko-build`). Preflight PASS → Build requires operator initiation per the L3 workflow.

## 2026-06-25 - BUILD - COMPLETE

* Work completed
    - Implemented the full `stockroom.ingest` package TDD, one RED→GREEN commit per plan step (1-11):
        1. Fixtures corrected to faithful per-harness roots (encoded project dirs, real subagent nesting + trimmed `meta.json` + `agent-name`), added robustness/pathological Claude fixtures and a synthetic `ai-code-tracking.db` pytest builder; parser-agnostic fixture-integrity test.
        2. `model.py` — `NormalizedSession`/`Message`/`ToolCall` dataclasses (schema-mapped, one-meaning-per-field).
        3. `cursor.py` — linear clean-room parser (dense ordinals, previous-kept parents, `turn_ended` boundary, empty-text kept, subagent `agent_type` from parent Task input).
        4. `claude.py` — allowlist parser: `parentUuid`-tree → nearest-kept-ancestor parents, per-message model/usage, `thinking`/`tool_result` drops, metadata folding (`ai-title`/`custom-title`/`agent-name`), ignore-unknown-types, subagent linkage via `meta.json`.
        5. `sources.py` — discovery + encoded-project-dir decode + `(mtime, path)` watermark filter (env-overridable roots).
        6. `enrich.py` — optional `ai-code-tracking.db` reader; graceful no-op when absent/malformed.
        7. `writer.py` — idempotent delete-then-insert per `(harness, session_id)` + `_sync_state` upsert; untruncated JSON `tool_input`.
        8. `ingest()` orchestrator wiring discover→parse→enrich→write→watermark; **golden ingest-output snapshot** (`expected_rows.json`) asserted byte-for-byte.
        9. `python -m stockroom.ingest` CLI (`--full`, `--harness`) with subprocess smoke tests exercising the real `warehouse.open()` RW path.
        10. Docs reconciled — `techContext.md` gained an Ingest (ETL) section pointing at the package, env conventions, golden snapshot, and fixtures.
        11. Green gate: `make ci` = **152 passed**, ruff lint+format clean, REUSE compliant (path-based AGPL, 142/142).
* Decisions / notes
    - Claude timestamps normalized to naive UTC for the timezone-naive `TIMESTAMP` column.
    - Golden snapshot normalizes machine-specific data (relative `source_path`, ISO datetimes, parsed `tool_input`, `_sync_state` excluded) so it tests reconstruction logic, not environment.
* Deferred to REFLECT
    - Durable `systemPatterns.md` entry for the clean-room-allowlist-parser + positional-identity + golden-ingest-snapshot pattern.
    - Real-data enrichment validation (`ai-code-tracking.db` absent on this machine).
* Next
    - BUILD → QA (autonomous). Run `/niko-qa` for the L3 post-implementation semantic review.
