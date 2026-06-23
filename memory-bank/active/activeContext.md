# Active Context

## Current Task: p0-foundations
**Phase:** PREFLIGHT - COMPLETE (PASS with advisories) — STOPPED for operator review before build

## What Was Done
- Researched the canonical `slobac` dual-manifest template (in the plugins cache) for exact manifest, release-please, REUSE, and CI conventions — fully reusable (operator's own template).
- Confirmed the O9 torch spike already validates the riskiest Phase 0 mechanism (hermetic lock + torch exclusion).
- Wrote the full Level 3 plan to `tasks.md`: 4 components, a test-first plan whose tests encode the acceptance criteria (torch-free hermetic lock; lockstep manifest versions), 5 ordered TDD steps, tech validation, and challenges.
- Resolved all open questions in-plan (high confidence) — no creative phase needed. One decision is surfaced for operator confirmation at preflight: the **app-bearing directory** = dedicated `skills/stockroom/` (vs. folding into `sr-initialize`).

## Recent Decisions (operator review, revised plan)
- **Engine home = `skills/sr-search/`** (operator's lead — the core entrypoint), shipping a **skeleton `SKILL.md`** in Phase 0 (operator confirmed skeleton skills are acceptable; real search behavior lands Phase 2). Alternative `sr-initialize` flagged; one-word veto. Replaces the earlier rejected `skills/stockroom/` dummy-dir idea.
- **PLUGIN_ROOT resolution** (cursor-warehouse's own invention, operator-cleared to crib): check-once-on-startup + `find -L` dev fallback + torch-safe `uv run --project --no-sync`. Recorded in `systemPatterns.md` for future phases.
- **REUSE/SPDX licensing is REQUIRED and enforced** (operator: intentional) — AGPL base on code, PPL-S layered on prompt content, AGPL re-asserted on code within `skills/**`; `reuse lint` in CI + a test. Not advisory.
- **Releases:** Phase 0 proves config + lockstep; operator flips real releases on via GitHub after merge. Confirmed.
- uv shape: `package = false` (run-in-place, no build backend), `src/` layout. Tooling `ruff`/`pytest`/`reuse`; runtime `duckdb`+`sentence-transformers`+`numpy` locked now (to *prove* torch exclusion).

## Next Step
- Plan revised post-preflight; preflight re-validated (still PASS). STILL STOPPED for operator review. Awaiting go/no-go (`/niko-build`) — or confirmation of `sr-search` vs `sr-initialize`.
