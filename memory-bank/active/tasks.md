# Tasks — p1-data-backbone

**Task:** Phase 1 — Schema, Database, Ingest, and Migrations

Level 4 project. Milestone decomposition is produced by the L4 Plan phase (`milestones.md`); each milestone is executed as its own L1–L3 sub-run with its own task checklist.

## Preflight findings (2026-06-24) — PASS with advisories

- **Amendment (applied):** Milestone 1 authors the DDL directly as the `migrations/0001` file so milestone 2 wraps it with no later file move; keeps milestones 1 and 2 non-overlapping.
- **Amendment (applied, radical-innovation):** Milestone 1 commits the field-enumeration record and shared real + pathological transcript fixtures as durable artifacts, reused by milestone 3's ingest tests and future-harness onboarding.
- **Advisory (for milestone 2 sub-run):** The "data-preserving upgrade under concurrent load" proof needs a representative *second* migration (a test-only `000N` is acceptable); the initial schema as `0001` on an empty DB does not by itself exercise a populated forward upgrade.
- **Advisory (for milestone 2 classification):** Migration framework trends toward L4 in the generic decision tree; confirm it classifies L3 at sub-run start and split it if the lock/concurrency design balloons.
- **TDD:** Per-unit test-before-code ordering is the responsibility of each sub-run's own plan phase; every milestone is marked test-first and the test-first invariant is recorded in `milestones.md`.
