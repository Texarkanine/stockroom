# Active Context

## Current Task: Workspace identity vs. real path (`project_id` + `cwd` recovery) (milestone 4 of `p1-data-backbone`, Level 2 sub-run)

**Phase:** REFLECT COMPLETE

## What Was Done

- **PLAN + PREFLIGHT (PASS):** full L2 plan in `tasks.md`; `encode` transform locked empirically; no-fabrication round-trip invariant added at preflight.
- **BUILD (complete, green `make ci` — 168 passed):**
    - `paths.py` resolver (`encode`/`encode_for`/`resolve_cwd`) + `test_ingest_paths.py` (committed earlier).
    - `0002_workspace_identity.sql` (drop `project_path`, add `project_id`); `test_schema_0002.py` + cumulative `0002_snapshot.json`; new `migrated_con` fixture.
    - Atomic rename across `model`/`sources`/`writer`/orchestrator: verbatim `project_id`; Cursor `cwd` via re-encode-and-match over in-band texts; Claude keeps record `cwd`; subagents inherit; dropped `decode_project_dir`; refreshed parser docstrings.
    - Two new Cursor fixtures (`recover-inband` hyphen-leaf recovery, `ambiguous-nopath` honest NULL); regenerated `expected_rows.json`; updated transcripts README + `techContext.md`.
    - Migration-framework tests updated to head version 2 (runner/discovery/warehouse open+concurrency).

## Build Surprise (recoverable, handled)

- Introducing `0002` flipped the migration head to v2, which broke several framework tests (hard-coded "v1/only 0001") **and** the CLI integration tests (real warehouse migrated to v2 while the un-renamed writer still used `project_path`). This coupled `0002` with the writer rename, so the planned per-step commits collapsed into **one atomic green change** (approach unchanged; only the commit grouping). Worth surfacing at REFLECT: preflight's dependency sweep tracked `project_path` consumers but missed migration-count assumptions.

## Next Step

- QA PASS → REFLECT complete (`reflection/reflection-p1-data-backbone-m4-cwd-recovery.md`; `systemPatterns.md` gained the verify-don't-invert cwd-recovery pattern). Milestone 4 of the `p1-data-backbone` L4 project is done. **Run `/niko` to advance to the next milestone.**
