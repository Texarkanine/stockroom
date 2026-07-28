# Project Brief

## User Story

As a maintainer preparing to socialize stockroom, I want GitHub issue form(s) and a PR template so that first-contact bug reports arrive with diagnosable context and PRs meet release/CI expectations without a round-trip.

## Use-Case(s)

### Use-Case 1: Bug report

A user hits a setup/runtime failure (torch, PATH/shim, hooks, ingest). They pick a Bug report form, paste `stockroom doctor` (and other load-bearing fields), and the maintainer can triage without asking for basics.

### Use-Case 2: Feature request

A user proposes a change. They pick a Feature request form with enough structure to triage, without being squeezed through a bug form.

### Use-Case 3: Freeform / design issue

The maintainer (or anyone) opens a blank issue for design docs and non-bug/non-feature work. Blank issues remain enabled.

### Use-Case 4: Pull request

A contributor opens a PR. The template surfaces load-bearing expectations (especially conventional-commit PR title → release-please changelog) without restating all of `CONTRIBUTING.md`.

## Requirements

1. Add GitHub issue template(s) under `.github/ISSUE_TEMPLATE/` — at minimum bug report and feature request.
2. Investigate whether component-segregated issue forms earn their keep (field divergence across ingest/embed/dashboard/plugin/docs/etc.); only split if they do.
3. Design optimal fields from stockroom's real failure surfaces and contributor contracts — [#100](https://github.com/Texarkanine/stockroom/issues/100) / [#101](https://github.com/Texarkanine/stockroom/issues/101) sketches are ideas, not gospel.
4. Add a PR template (path/shape chosen for what's optimal).
5. Keep `blank_issues_enabled: true`.
6. Template prose: short, action-first (ADHD-friendly) — but do not omit load-bearing fields that deliver triage/release value.

## Constraints

1. Do not restate `CONTRIBUTING.md` / docs SSOT; link where needed.
2. No auto-labeling, project automation, or stale-bot in this task.
3. Prefer issue *forms* (YAML) where required fields matter; don't invent bureaucracy.

## Acceptance Criteria

1. Opening a new issue offers Bug report and Feature request (and any justified extras) plus blank issue.
2. Bug form collects what maintainers actually need for first-contact diagnosis (doctor output and other load-bearing context as determined in planning).
3. PR template pre-fills on new PRs and surfaces conventional-commit title + other load-bearing checklist items without drowning contributors.
4. Templates feel fillable by humans — concise labels/help, no verbal flourish.
