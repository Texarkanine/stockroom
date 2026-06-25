# Active Context

## Current Task: Migration framework (milestone 2 of `p1-data-backbone`, Level 3 sub-run)

**Phase:** PLAN - COMPLETE (creative resolved; ready for preflight)

## What Was Done

- Advanced the L4 project: milestone 1 checked off in `milestones.md`; its sub-run ephemeral files cleared (Step 2a). Milestone-1 reflection preserved. Classified milestone 2 (Migration framework) as **Level 3**.
- PLAN: component analysis + two planning POCs (DuckDB cross-process locking; `fcntl.flock` auto-release on WSL-internal ext4) pinned in `tasks.md`.
- CREATIVE (architecture): resolved the concurrency/lock design — `fcntl.flock` sidecar single-writer/migrator token over DuckDB's native lock + bounded reader backoff (`WarehouseBusyError`); `schema_version` is a runner-owned bootstrap table (not in `0001`). Doc: `creative/creative-warehouse-concurrency-locking.md`.
- PLAN finalized: proposed module layout (`migrations/` discovery, `migrate.py` runner, `warehouse.py` chokepoint), TDD test plan (5 test files incl. a multi-process concurrency suite), 9 ordered implementation cycles, technology validation (no new dependency), challenges.

## Operator Decisions (plan refinement, 2026-06-25, at the pre-build gate)

- **Drop `from __future__ import annotations` project-wide.** Not needed on `>=3.11`, not linter-enforced. New m2 modules omit it; a precursor sweep (impl step 0) removes it from the existing ~6 files for uniformity.
- **No Windows friendly-guard.** Native Windows fails fast at `import fcntl` (`ModuleNotFoundError`) long before any `flock`; that is already loud and Windows-native is out of v1 — leave the raw error.
- **Portability confirmed (analysis, no change needed):** the design works on M4 macOS, Linux, and Linux containers (incl. Docker Desktop's LinuxKit VM) when the warehouse is on a **local POSIX filesystem**. The only failure mode is a network/VM-shared FS (NFS, virtiofs/gRPC-FUSE) — an embedded-DB anti-pattern, not a flock-specific flaw. Captured as a generalized challenge bullet in `tasks.md`.

## Next Step

- 🧑‍💻 Operator-gated **Build** (`/niko-build`). PREFLIGHT is PASS (with advisories). Build implements the plan test-first, starting with the step-0 convention sweep.
