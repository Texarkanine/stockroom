# Project Brief

## User Story

As a dashboard user and SQL querier, I want sessions that share the same project path on this machine to share a `workspace_key` across harnesses so that Sessions by Project and ad-hoc queries can cross-reference them without merging different on-disk paths.

## Use-Case(s)

### Use-Case 1

Cursor and Claude both used `/home/mobaxterm/git/stockroom` (different `project_id` slugs). After ingest, both rows carry the same `workspace_key`; the chart shows one stockroom bar and `GROUP BY workspace_key` matches that view.

### Use-Case 2

Claude lite-rpg under `/mnt/v/...` and Cursor lite-rpg under `/home/...` keep different `workspace_key`s — same human “repo” intuition, different paths on disk, intentionally separate.

### Use-Case 3

A future harness registers its own ETL transform for `workspace_key` without changing Cursor/Claude strategies or mutating `project_id`.

## Requirements

1. Add nullable `sessions.workspace_key` via forward migration (next number after 0005).
2. Extensible per-harness ETL transforms to derive `workspace_key` from that harness’s `cwd` / `project_id` (registry/strategies); convergence contract: same machine + same `cwd` ⇒ same key when both can derive it.
3. Leave `project_id` harness-verbatim; do not rewrite identity.
4. When a harness cannot derive a key, store `NULL` (honest).
5. Populate on ingest insert/upsert; `--full` re-ingest backfills existing rows.
6. `metrics.projects()` (Sessions by Project) groups/ranks by `workspace_key` so chart and SQL share the key.
7. Document contract: migration header, paths/helper module, architecture warehouse identity, systemPatterns one-liner as needed.

## Constraints

1. Design authority: `memory-bank/active/creative/creative-project-rollup-layer.md`.
2. No global “strip non-alnum” normalize; no mutating `project_id`.
3. Verify-don’t-invert and one-meaning-per-column doctrines hold.
4. TDD; follow project test-running practices.

## Acceptance Criteria

1. Migration adds `workspace_key`; schema tests / contracts green.
2. Cursor + Claude sessions with identical `cwd` get identical non-NULL `workspace_key` after ingest.
3. Different `cwd`s get different keys (lite-rpg mount case).
4. NULL `cwd` (when strategy needs it) ⇒ NULL `workspace_key`.
5. Sessions by Project rolls up on `workspace_key`; queriers can `GROUP BY workspace_key` to match.
6. Adding a harness strategy is a localized extension point (documented).
7. Docs updated for the contract.
