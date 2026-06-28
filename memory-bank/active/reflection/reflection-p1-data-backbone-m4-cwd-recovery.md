---
task_id: p1-data-backbone-m4-cwd-recovery
date: 2026-06-28
complexity_level: 2
---

# Reflection: Workspace identity vs. real path (`project_id` + `cwd` recovery)

## Summary

Replaced the lossy, fabricating `sessions.project_path` with two single-meaning columns — `project_id` (verbatim encoded slug; the grouping identity) and a re-semantic, honestly-NULL `cwd` (real project root) — shipped as the project's first real schema-changing, data-preserving migration (`0002`) through the m2 framework. Succeeded: `make ci` green (168 passed), with a corpus-wide no-fabrication round-trip invariant proving a fabricated path can't be stored.

## Requirements vs Outcome

Every planned requirement delivered, nothing dropped or descoped: the `paths.py` verify-don't-invert resolver, the structural `0002` migration + cumulative `0002_snapshot.json` + `migrated_con` fixture, verbatim `project_id` stamping, Cursor `cwd` recovery via re-encode-and-match (with subagent inheritance), Claude's authoritative record `cwd` retained (the latent lossy-decode stamping removed), `decode_project_dir` deleted, two new recovery fixtures, and the regenerated ingest golden. The preflight-added no-fabrication round-trip invariant shipped as a general property test. No requirements were added beyond that.

## Plan Accuracy

The plan's *content* (files, design, the empirically-locked `encode` transform) was exactly right; its *commit granularity* was wrong. The plan prescribed one green commit per TDD step, but introducing `0002` advances the migration head to v2 — which (a) breaks every framework test that hard-coded "version 1 / only 0001 exists" and (b) breaks the CLI integration tests, because `warehouse.open()` migrates the real warehouse to v2 while the not-yet-renamed writer still inserts `project_path` (BinderError). That coupling made the planned per-step boundaries non-green, so `0002` + the writer/model/sources/orchestrator rename had to land as a single atomic commit. The identified challenges (snapshot determinism, no-backfill, frozen `0001`, `schema_con`→`migrated_con` split) all materialized as expected; the surprise was purely the cross-test version-coupling that preflight's dependency sweep didn't model.

## Build & QA Observations

Build went smoothly once the coupling was recognized — RED→GREEN held throughout, and the empirical `encode` lock from PLAN meant zero guesswork on the transform. The main judgment call was reframing the commit strategy mid-build (recoverable, approach unchanged) rather than forcing artificial green checkpoints. QA was clean (no rework): the residual `project_path` sweep confirmed every remaining reference is intentional (the `0002` migration, its pre-migration seed test, and the frozen `0001` artifacts).

## Insights

### Technical
- **A new migration is a test-suite-wide event, not a local file add.** Any test asserting "latest version == N", "only these migrations exist", or that opens the real warehouse implicitly depends on the migration *head*. Adding `0002` rippled into `test_migrate_runner`, `test_migrations_discovery`, `test_warehouse_open`, `test_warehouse_concurrency`, *and* the CLI integration tests. Future migrations should budget for updating these head-version assertions as part of the same change.
- **Verify-don't-invert is the durable shape for any lossy harness encoding.** Because `encode` is many-to-one it can't be inverted, but it *can* be recomputed forward and checked (`encode_for(harness, candidate) == slug`). That makes the false-positive rate zero by construction and the failure mode a clean NULL — generalizes to any future slug/id recovery.

### Process
- **Preflight's dependency sweep should include "migration-count / head-version assumptions," not just symbol consumers.** It correctly enumerated every `project_path` consumer but missed the tests coupled to the migration *head*. A cheap addition to the preflight checklist when a task adds a migration.
- **"Every commit stays green" can legitimately override "one commit per plan step."** When steps are coupled through a shared global (here, the migration head), collapsing them into one atomic green commit is the correct bisect-safe move — the TDD discipline lives in the RED→GREEN *iteration*, not necessarily in the commit count.

### Million-Dollar Question

If honest workspace identity had been a foundational assumption, `0001` would have declared `project_id TEXT` + `cwd TEXT` from the start (no `project_path` ever), discovery would have carried the verbatim slug from day one, and `cwd` recovery would have been part of the original parser/orchestrator contract — eliminating the `0002` migration, the dual-snapshot churn, and the entire `schema_con`/`migrated_con` split. That said, the migration was *valuable on its own terms*: it dogfooded the m2 framework's first real data-preserving upgrade, which was an explicit Phase-1 "Done When" goal — so the non-foundational path bought a genuine framework-validation milestone, not just rework.
