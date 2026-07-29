---
task_id: github-issue-and-pr-templates
complexity_level: 2
date: 2026-07-28
status: completed
---

# TASK ARCHIVE: GitHub Issue Forms & PR Template

## SUMMARY

Shipped bug + feature GitHub issue forms (shared Area dropdown, blank issues enabled, troubleshooting `contact_links`) and a short PR template, pinned by packaging-style structural tests. Addresses #100/#101 launch-readiness; draft PR #103 opened on `issue-templates`.

## REQUIREMENTS

- Issue forms under `.github/ISSUE_TEMPLATE/` — bug report and feature request minimum.
- Investigate component-split; only split if field sets diverge (they did not — Area dropdown instead).
- Design fields from real triage surfaces; #100/#101 sketches are ideas, not gospel.
- PR template for conventional-commit / release-please + CI expectations without restating CONTRIBUTING.
- `blank_issues_enabled: true`.
- ADHD-short prose; keep load-bearing fields (especially doctor-first on bugs).

## IMPLEMENTATION

TDD: `skills/sr-search/tests/test_github_templates.py` (8 structural tests via `repo_root` + `yaml.safe_load`) → then templates.

Key files:
- `.github/ISSUE_TEMPLATE/config.yml` — blanks on; Troubleshooting contact link
- `.github/ISSUE_TEMPLATE/bug_report.yml` — doctor probe first (required), Area, version, harness, expected/actual; optional logs/checkboxes
- `.github/ISSUE_TEMPLATE/feature_request.yml` — Area + problem/proposal; no doctor tax
- `.github/pull_request_template.md` — CONTRIBUTING link, conventional-commit title + changelog consequence, `make ci` / docs / REUSE
- `CONTRIBUTING.md` — commit-type gate aligned with release-please (`feat`/`fix` release; `chore` = no-release; drop `docs` as release type)

Preflight amendments: contact_links, `[Bug]: `/`[Feature]: ` title prefixes, no direct PyYAML dep (transitive via huggingface-hub).

Post-reflect fix: PR title guidance corrected so only `feat`/`fix` release; `chore` is the must-not-release escape.

## TESTING

- Full TDD red→green on `test_github_templates.py`.
- `make ci` (NODE=22) and `make docs-build` green.
- `/niko-qa` PASS after one trivial fix: PR template links CONTRIBUTING visibly.

## LESSONS LEARNED

- GitHub issue-form YAML treats unquoted values with `:` / `...` as structure — quote placeholders that look like mappings (`os: ...`).
- Field needs converge across components; Area dropdown beats N near-duplicate forms.
- Issue sketches as "ideas not gospel" plus a troubleshooting-vs-doctor field review prevented over-building.

## PROCESS IMPROVEMENTS

- Preflight amendments (contact_links, title prefixes) were the right place to add small UX without reopening plan scope.

## TECHNICAL IMPROVEMENTS

None beyond the shipped templates.

## NEXT STEPS

- Land draft PR #103 (closes #100/#101).
- Remaining launch-readiness tracked separately: #102 (hook graphics / demo GIFs).
