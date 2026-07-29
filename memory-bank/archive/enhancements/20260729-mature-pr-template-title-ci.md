---
task_id: mature-pr-template-title-ci
complexity_level: 2
date: 2026-07-29
status: completed
---

# TASK ARCHIVE: Mature PR Template + Title CI Check

## SUMMARY

Rewrote `.github/pull_request_template.md` to the Unautomatable-Only (Option D) design — five prose sections, no checklist — and added `.github/workflows/pr-title.yaml` (`amannn/action-semantic-pull-request@v6`) so conventional-commit titles are a hard CI gate. PR [#106](https://github.com/Texarkanine/stockroom/pull/106) is open on `pr-template-improve`.

## REQUIREMENTS

- Five prose sections: Goal, What's here, How I know it works, What changes for a user, Effect on an existing warehouse.
- No checklist; release-consequence guidance in a top-of-body HTML comment.
- Keep lowercase path and visible `CONTRIBUTING.md` link.
- Conventional-commit PR title CI on `pull_request` (feat/fix release; chore must-not-release; exclude `docs`).
- Do not re-add prose structural tests of the kind deleted in #103.
- Open a PR with the work.

## IMPLEMENTATION

Creative selected Option D over Evidence Ledger / Narrative+Teeth / Divergence-First: nothing CI-checkable belongs in the template; a checkbox launders claims (#103 proved it). Title lint earns deleting the checklist — both must ship together or the policy regresses to nothing.

Key files:
- `.github/pull_request_template.md` — Option D body
- `.github/workflows/pr-title.yaml` — types allowlist excludes `docs`; `pull_request` (not `pull_request_target`); `chore(main): release …` remains valid for release-please
- `memory-bank/techContext.md` — notes the new workflow

Post-QA correction (operator): deleted `test_pr_template_and_title_ci.py`. Plan/TDD pressure invented a "structural marker" loophole (headings/link/no-checklist) that still pytest-locks markdown; operator rejected it — prose/docs/templates are not code and have no regression value from pytest. Follow-up carve-out tracked in `.cursor-rules` #95.

No `CONTRIBUTING.md` edit (creative/preflight: template + CI carry the policy).

## TESTING

- Initial TDD red→green on structural tests, then those tests were removed per operator.
- `make format` + `make ci` green before reflect (797 passed, 4 skipped; REUSE clean).
- `/niko-qa` PASS (simplified types assert; techContext note).
- Title CI validated by workflow presence and allowlist design; live check runs on PR #106.

## LESSONS LEARNED

- Once "don't put CI-checkable items in the template" is hard, the checklist dies entirely; title check must land in the same change.
- always-tdd + L2 plan pressure will invent "structural marker" tests for markdown; that is still testing prose — refuse it. Prefer process carve-outs (`.cursor-rules` #95) over pytest locks on templates.
- Dedicated `pr-title.yaml` keeps `ci.yaml` engine-focused; audit new GHA pins for releases/activity before adopting (amannn v6 still maintained as of mid-2026).

## PROCESS IMPROVEMENTS

- Preflight/plans that propose testing instructional prose or template headings should FAIL, not merely allow skipping (operator direction for always-tdd carve-out).

## TECHNICAL IMPROVEMENTS

None beyond the shipped template + title workflow.

## NEXT STEPS

- Land PR #106.
- Separate concern (creative follow-on): `memory-bank/active/*` plan-staleness is a large review-comment category and no PR template can fix it.
