# Task: Mature PR Template + Title CI Check

* Task ID: mature-pr-template-title-ci
* Complexity: Level 2
* Type: Simple enhancement

Rewrite `.github/pull_request_template.md` to the Unautomatable-Only (Option D) design from `memory-bank/active/creative/creative-pr-template-maturity.md`, add a conventional-commit PR title check in CI, and open a PR. Filename stays lowercase. No checklist; no prose structural tests of the kind deleted in #103.

## Test Plan (TDD)

### Behaviors to Verify

- Template present: `.github/pull_request_template.md` exists at repo root → test finds the file
- Template has Unautomatable-Only sections: file contains headings `## Goal`, `## What's here`, `## How I know it works`, `## What changes for a user`, `## Effect on an existing warehouse` → assert presence
- Template links CONTRIBUTING: file contains a markdown link to `CONTRIBUTING.md` → assert presence
- Template has no checklist: file does not contain `- [ ]` → assert absence (checklist moved to CI / prose claims)
- Title CI workflow present: a workflow under `.github/workflows/` validates PR titles as conventional commits → assert file exists and references the semantic-pull-request action (or equivalent title-lint step)
- Title CI types match CONTRIBUTING release gate: allowed types include `feat`, `fix`, `chore` and exclude `docs` (discouraged — does not release/republish Pages) → assert types config

### Edge cases

- Empty / missing template file → packaging-style test fails (existence)
- Title with `docs:` type → CI title job fails (enforces CONTRIBUTING)
- Title with `feat!:` breaking change → CI title job passes (conventional commits allows `!`)
- Bot/release-please PR titles — release-please uses `chore(main): release …` which must pass

### Test Infrastructure

- Framework: pytest (engine suite under `skills/sr-search/tests/`)
- Test location: `skills/sr-search/tests/`
- Conventions: packaging-style structural tests using `repo_root` fixture (see `test_packaging.py`)
- New test files: `skills/sr-search/tests/test_pr_template_and_title_ci.py`
- Explicitly **not** testing instructional prose / HTML comment wording (honors #103 `fix(docs): don't test prose`)

## Implementation Plan

1. **Write failing structural tests**
   - Files: `skills/sr-search/tests/test_pr_template_and_title_ci.py`
   - Changes: new tests for template path, five headings, CONTRIBUTING link, no `- [ ]`, and title-CI workflow presence + allowed types (`feat`/`fix`/`chore`, no `docs`)

2. **Rewrite PR template**
   - Files: `.github/pull_request_template.md`
   - Changes: replace checklist body with v2 draft from creative doc (Goal / What's here / How I know it works / What changes for a user / Effect on an existing warehouse); release guidance in top HTML comment; keep CONTRIBUTING link

3. **Add PR title CI workflow**
   - Files: `.github/workflows/pr-title.yaml` (new; keep `ci.yml` focused on engine)
   - Changes: job on `pull_request` types `opened|edited|synchronize|reopened` using `amannn/action-semantic-pull-request@v6` with types `feat`, `fix`, `chore`, `refactor`, `perf`, `test`, `build`, `ci`, `revert` (exclude `docs`); `pull_request_target` **not** used (safer; works for same-repo PRs; fork PRs still get the check on `pull_request`)
   - Permissions: `pull-requests: read` only as needed by the action

4. **Align CONTRIBUTING if needed**
   - Files: `CONTRIBUTING.md`
   - Changes: one sentence under Pull requests that CI enforces conventional-commit titles (do not duplicate the type table)

5. **Verify**
   - Run the new tests (red→green), then `make ci` / relevant slice
   - Open PR with the new template filled honestly

## Technology Validation

New GitHub Action dependency: `amannn/action-semantic-pull-request@v6` (pinned major; Dependabot already watches Actions). No Python/runtime dependency. No local PoC required beyond workflow YAML review — action is marketplace-standard and only runs on GitHub.

## Dependencies

- Creative decision: `memory-bank/active/creative/creative-pr-template-maturity.md`
- Existing: `CONTRIBUTING.md` conventional-commit policy; Dependabot for GHA updates
- Existing: `repo_root` fixture in engine tests

## Challenges & Mitigations

- **Fork PRs + secrets:** `amannn` with `pull_request` (not `pull_request_target`) uses `GITHUB_TOKEN` and works for forks without writing to the base; prefer this over `pull_request_target`.
- **release-please titles:** `chore(main): release x.y.z` must remain valid — `chore` is in the allowlist.
- **Temptation to re-test prose:** resist; only structural markers (headings, link, no checklist, workflow types).
- **Dependabot noise:** new Action will get update PRs — acceptable; already have GHA Dependabot.

## Pre-Mortem

- **Plan failed because title check blocked every PR including bots:** already covered by Challenge (allow `chore`; release-please uses it).
- **Plan failed because we reintroduced #103's prose tests and deleted them again:** mitigated by Test Plan explicitly excluding prose and by creative constraint.
- **Plan failed because template was inadequate again (sections ignored):** social force only; cannot be fixed by more checkboxes — already the design premise. No plan change.
- **Plan failed because `amannn` was overkill vs inline bash:** if Dependabot/supply-chain pushback, swap to inline regex job in same workflow file without changing the test contract (assert "title lint step exists").

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Pre-Mortem complete
- [ ] Preflight
- [ ] Build
- [ ] QA
