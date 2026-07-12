# Task: release-quality-docs

* Task ID: release-quality-docs
* Complexity: Level 2
* Type: documentation content draft (search + dashboard pages)

Draft `docs/user-guide/search.md` and `docs/user-guide/dashboard.md` to finished user-guide quality.

## Test Plan (TDD)

Docs-only — Verification Plan is the gate (TDD N/A for code):

1. Acceptance sweep B1–B6 before claiming complete.
2. `make docs-build` (`properdocs build --strict`).

### Behaviors to Verify

- **B1 Search default**: Page steers readers to `sr-search` when unsure of structured vs meaning-based.
- **B2 Three skills**: Overview of `sr-search`, `sr-query`, `sr-semantic` with when-to-use and Cursor/Claude slash forms — no flag encyclopedias.
- **B3 Dashboard overview**: Explains local read-only metrics UI (port 58008), auto-launch vs `sr-dashboard`, machine-scoped singleton notes without forking troubleshooting.
- **B4 Screenshots**: At least the metrics and session views from `docs/img/` used where they clarify (or explicitly skipped with rationale).
- **B5 DRY**: using-skills / Quickstart / Advanced / Troubleshooting linked, not forked; using-skills dashboard essay slimmed to pointers if still duplicative.
- **B6 Build**: `make docs-build` PASS; no todo placeholders on either page.

### Edge cases

- **E1** DuckDB CLI screenshot: Advanced owns raw DuckDB — do not make search.md a second CLI tutorial; at most a one-line escape hatch + image optional.
- **E2** using-skills not in `.pages` nav: leave nav alone unless needed; still keep file DRY so it does not contradict new pages.

### Test Infrastructure

- Framework: properdocs / `make docs-build`
- New test files: none

## Implementation Plan

1. **Draft search.md**
   - Files: `docs/user-guide/search.md`
   - Changes: Lead with how to search (`sr-search`); sections for the three skills; link Advanced CLI for bare `stockroom query`/`semantic`; link Ingest if warehouse empty / Torch if semantic fails.
2. **Draft dashboard.md**
   - Files: `docs/user-guide/dashboard.md`
   - Changes: What it is; `sr-dashboard` / auto-launch; metrics vs session views with `stockroom-dashboard-top-light.png` and `stockroom-dashboard-convo-light.png`; deep-link / export at overview altitude; link Troubleshooting for port/stale issues.
3. **DRY using-skills**
   - Files: `docs/user-guide/using-skills.md`
   - Changes: Point After setup / Dashboard notes at search.md and dashboard.md; keep skills table as discovery index.
4. **Verify**
   - `make docs-build`; acceptance B1–B6.

## Technology Validation

No new technology - validation not required

## Dependencies

- Skill descriptions: `skills/sr-{search,query,semantic,dashboard}/SKILL.md` (paraphrase, don't fork)
- Images: `docs/img/stockroom-dashboard-*.png`
- Style refs: ingest / quickstart / installed-layout / torch

## Challenges & Mitigations

- **Overlap with using-skills**: Mitigation — using-skills = discovery table; search/dashboard = depth.
- **Screenshot noise**: Mitigation — two purposeful images with captions; skip duckdb CLI shot on these pages.

## Pre-Mortem

- **Pages become SKILL mirrors**: Cut flags; keep when-to-use + slash forms.
- **using-skills left as competing SSOT**: Already covered by Step 3.

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Pre-Mortem complete
- [x] Preflight
- [ ] Build
- [ ] QA
