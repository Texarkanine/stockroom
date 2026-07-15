# Project Brief

## User Story

As a maintainer, I want Dependabot configured for both UV package roots and GitHub Actions so that dependency updates arrive as well-scoped, conventionally-prefixed PRs with majors isolated and minor/patch updates groupable where appropriate.

## Use-Case(s)

### Use-Case 1

Dependabot opens a PR when a UV dependency in the docs root or engine root has an update, using the configured grouping, cooldown, and commit-message prefixes.

### Use-Case 2

Dependabot opens a PR when a GitHub Actions workflow uses an outdated action, without grouping or cooldown, with the `chore(deps-ci)` commit prefix.

## Requirements

1. Add `.github/dependabot.yaml` covering three update surfaces: UV docs root (`/`), UV engine (`/skills/sr-search`), and GitHub Actions (`/`).
2. UV updates: always split major bumps into their own PRs; allow grouping of minor + patch.
3. UV updates: 7-day cooldown.
4. GitHub Actions: no grouping (actions are pinned by major tag); no cooldown.
5. Commit message prefixes:
   - `chore(deps-ci)` for GitHub Actions
   - `chore(deps-dev)` for UV engine development dependencies
   - `chore(docs)` for docs-root UV dependencies
   - `fix(deps)` for UV engine non-dev (production) dependencies
6. Follow structural patterns from `../a16n` and `../inquirerjs-checkbox-search` (ecosystem split, major isolation via grouping of minor/patch only), adapted for UV + the GHA no-group policy above.

## Constraints

1. This repo has no npm dependencies — npm ecosystem entries are not in scope.
2. UV roots are the root docs toolchain and `skills/sr-search` engine only.
3. Prefer matching reference-repo conventions (schedule, assignees, PR limits) where the brief does not override them, as long as they do not conflict with the requirements above.

## Acceptance Criteria

1. `.github/dependabot.yaml` exists and is valid Dependabot config (version 2).
2. Three update entries exist for the two UV directories and GitHub Actions as specified.
3. UV entries group only minor + patch (majors remain ungrouped / separate PRs) and set a 7-day cooldown.
4. GitHub Actions entry has no groups and no cooldown.
5. Commit-message prefixes match the four prefixes listed in Requirements.
