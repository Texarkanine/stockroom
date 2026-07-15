---
task_id: dependabot-config
complexity_level: 2
date: 2026-07-15
status: completed
---

# TASK ARCHIVE: dependabot-config

## SUMMARY

Added `.github/dependabot.yaml` for UV docs (`/`), UV engine (`/skills/sr-search`), and GitHub Actions: major bumps isolated, UV minor+patch grouped with a 7-day cooldown, GHA ungrouped, conventional commit prefixes. Operator later renamed the docs prefix to `chore(deps-docs)` and dropped the GHA `cooldown.default-days: 0` block.

## REQUIREMENTS

1. Three update surfaces: UV `/`, UV `/skills/sr-search`, github-actions `/` (no npm).
2. UV: group minor + patch only (majors ungrouped); 7-day cooldown.
3. GitHub Actions: no grouping; no cooldown.
4. Commit prefixes: docs UV, engine prod/dev UV, and GHA (`chore(deps-ci)`).
5. Follow a16n / inquirerjs-checkbox-search structural patterns where the brief was silent.

## IMPLEMENTATION

Single deliverable: `.github/dependabot.yaml` (version 2). Monthly Monday 09:00; assignees `Texarkanine`; PR limits 10 (uv) / 5 (gha). Docs UV sets both `prefix` and `prefix-development` to `chore(deps-docs)`; engine uses `fix(deps)` / `chore(deps-dev)`; GHA uses `chore(deps-ci)`. Schedule/assignees/PR limits taken from sibling reference repos. `memory-bank/techContext.md` got a CI/release pointer to the Dependabot file. No docs page added (none existed; brief did not require).

## TESTING

Operator override: no automated pytest for Dependabot YAML — GitHub validates on ingest. Verification was review against the brief (ecosystems, grouping, UV cooldown, prefixes). `/niko-preflight` PASS; `/niko-qa` PASS after test-suite debris was removed.

## LESSONS LEARNED

### Technical

- Dependabot's platform default cooldown is 3 days; omitting the GHA cooldown block does not opt out. The build initially set `default-days: 0`; the operator later removed that block intentionally.

### Process

- Do not pytest-contract platform config (Dependabot, release-please, etc.) unless asked — the suite is ceremony without product signal.
- Plan over-indexed on TDD for YAML policy; shipping the config alone (patterned on sibling repos) was the right end state.

## PROCESS IMPROVEMENTS

Treat “tests for platform YAML” as opt-in for this repo unless the operator requests them at plan time.

## TECHNICAL IMPROVEMENTS

None. Soft follow-up only if Dependabot’s cooldown semantics for omitted blocks change again — re-confirm GHA “no cooldown” against current GitHub docs.

## NEXT STEPS

None. Memory bank ready for the next task.
