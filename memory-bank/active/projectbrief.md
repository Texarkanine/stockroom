# Project Brief: Mature PR Template + Title CI Check

## Goal

Replace the short checklist-style `.github/pull_request_template.md` with the Option D (Unautomatable-Only) design resolved in `memory-bank/active/creative/creative-pr-template-maturity.md`, and add a conventional-commit PR title check in CI so the checklist can be deleted without losing that gate.

## Requirements

1. Rewrite `.github/pull_request_template.md` to five prose sections:
   - Goal
   - What's here
   - How I know it works (tests named, platform exercised, optional transcript)
   - What changes for a user
   - Effect on an existing warehouse
2. No checklist. Release-consequence guidance lives in a top-of-body HTML comment (title sits above the body in GitHub's UI).
3. Keep the visible link to `CONTRIBUTING.md`.
4. Keep the existing lowercase path `.github/pull_request_template.md` (repo convention; GitHub accepts either casing).
5. Add a conventional-commit PR title check on `pull_request` in CI — `feat`/`fix` release, `chore` must-not-release (and whatever else conventional commits allow that release-please already understands). This is what earns deleting the checklist.
6. Do not re-add prose structural tests of the kind deleted in #103 (`fix(docs): don't test prose`). At most assert the template file exists if a test is warranted.
7. Open a PR with the work.

## Out of scope

- Fixing `memory-bank/active/*` plan-staleness workflow (separate concern).
- Multiple named PR templates under `.github/PULL_REQUEST_TEMPLATE/`.
- Changing `CONTRIBUTING.md` beyond what's strictly required if the title CI check needs a one-line pointer.

## Design authority

`memory-bank/active/creative/creative-pr-template-maturity.md` (v2 draft is selected).
