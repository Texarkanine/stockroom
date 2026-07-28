# Task: github-issue-and-pr-templates

* Task ID: github-issue-and-pr-templates
* Complexity: Level 2
* Type: simple enhancement

Add GitHub issue forms (bug + feature) and a short PR template so first-contact reports and PRs carry load-bearing triage/release context. Design from stockroom surfaces; #100/#101 sketches are inputs, not specs.

**Component-split decision:** Do **not** create per-component issue forms. Troubleshooting spans install/hooks, shim, ingest/schedule, search, torch/semantic, dashboard — but the *fields* needed for triage converge: `stockroom doctor probe` + version + harness + what-you-ran + expected/actual. Divergence is routing (where it hurts), not form shape. Use one **Area** dropdown on both forms instead of N near-duplicate YAMLs.

## Test Plan (TDD)

### Behaviors to Verify

- [Bug form exists]: repo has `.github/ISSUE_TEMPLATE/bug_report.yml` → parses as YAML with `name`, `body` list
- [Feature form exists]: repo has `.github/ISSUE_TEMPLATE/feature_request.yml` → same structure
- [Blank issues allowed]: `.github/ISSUE_TEMPLATE/config.yml` has `blank_issues_enabled: true`
- [Troubleshooting contact link]: `config.yml` has a `contact_links` entry pointing at the troubleshooting docs URL
- [Doctor field load-bearing]: bug form body has a required `textarea` whose label/description mentions `stockroom doctor` (probe), and it appears before expected/actual narrative fields
- [Area on both forms]: bug and feature forms each include a required `dropdown` for area/component routing
- [Harness on bug form]: bug form has a required harness dropdown including Cursor, Claude Code, and CLI-only/neither
- [Pre-submit hints]: bug form has checkboxes covering troubleshooting doc, torch/`sr-initialize`, and Cursor third-party plugins setting
- [PR template exists]: `.github/pull_request_template.md` exists and mentions conventional commits / changelog consequence and `make ci`
- [No feature-request doctor tax]: feature form does not require doctor output
- [Edge: YAML invalid]: malformed YAML → parse fails (implicit via yaml.safe_load in tests)
- [Edge: blank disabled]: if `blank_issues_enabled` were false → test fails (pin the constraint)

### Test Infrastructure

- Framework: pytest (engine project)
- Test location: `skills/sr-search/tests/`
- Conventions: packaging/hygiene style — `repo_root` fixture, assert repo-root artifacts (see `test_packaging.py`, `test_skill_hygiene.py`)
- New test files: `skills/sr-search/tests/test_github_templates.py`

## Implementation Plan

1. **Failing tests first** — stub then implement `test_github_templates.py` covering behaviors above (forms missing → fail).
   - Files: `skills/sr-search/tests/test_github_templates.py`
   - Changes: new test module; use `yaml.safe_load` (PyYAML available via engine/docs deps — verify; if not in engine lock, use a minimal structural parse or add assertion via `ruamel`/`yaml` already present)

2. **`config.yml`** — blank issues + triage contact link.
   - Files: `.github/ISSUE_TEMPLATE/config.yml`
   - Changes:
     - `blank_issues_enabled: true`
     - `contact_links`: one entry → Troubleshooting docs (`about`: check common install/torch/hooks/shim fixes before filing). Surfaces above the template chooser without blocking blanks.

3. **`bug_report.yml`** — single optimal bug form (ADHD-short labels; keep load-bearing fields).
   - Files: `.github/ISSUE_TEMPLATE/bug_report.yml`
   - Metadata: `title: "[Bug]: "`, `labels: ["bug"]`
   - Fields (order):
     1. `markdown` — one short line: paste doctor first; link [Troubleshooting](https://texarkanine.github.io/stockroom/user-guide/troubleshooting/)
     2. `textarea` **stockroom doctor probe** — required; `render: shell`; description notes local paths; command `stockroom doctor probe`
     3. `dropdown` **Area** — required; options: Install / setup · Hooks / harness · Shim / PATH · Ingest / schedule · Search (SQL) · Semantic / torch · Dashboard · Docs · Other
     4. `input` **stockroom version** — required; placeholder `stockroom --version`
     5. `dropdown` **Harness** — required; Cursor · Claude Code · CLI only / neither
     6. `input` **Harness version** — optional; free text
     7. `textarea` **What you ran** — required; skill or CLI verbatim
     8. `textarea` **Expected** — required
     9. `textarea` **Actual** — required
     10. `textarea` **Logs** — optional; `$STOCKROOM_HOME/logs/`; `render: shell`
     11. `dropdown` **Restarted harness since install/update?** — optional; Yes · No · Unsure
     12. `checkboxes` **Before submit** — optional items (not required gates): read Troubleshooting; if torch/semantic read Torch + re-ran `sr-initialize`; Cursor: third-party Plugins/Skills/configs enabled
   - Labels: `bug` (form metadata, not a bot)

4. **`feature_request.yml`** — short form; no doctor.
   - Files: `.github/ISSUE_TEMPLATE/feature_request.yml`
   - Metadata: `title: "[Feature]: "`, `labels: ["enhancement"]`
   - Fields: short markdown · Area dropdown (same options) · Problem / motivation (required) · Proposal (required) · Alternatives (optional)

5. **PR template** — short; load-bearing checklist first items matter most.
   - Files: `.github/pull_request_template.md`
   - Content: link to CONTRIBUTING · What & why · Checklist: conventional-commit PR title (`feat`/`fix`/`chore`/`docs` only) + changelog consequence · tests-first · `make ci` · `make docs-build` (+ docs if contract changed) · `make reuse` · stays in scope · HTML comment for Niko/memory-bank
   - No type-of-change matrix (prefix already carries it)

6. **Run tests** — `pytest skills/sr-search/tests/test_github_templates.py` then full `make ci` / `make docs-build` as needed for gate.

7. **Docs/CONTRIBUTING** — no restatement. Optional one-line under CONTRIBUTING Pull requests pointing at templates only if it helps discoverability; default skip (GitHub UI surfaces them).

## Technology Validation

No new technology - validation not required. Issue forms use GitHub's native YAML schema ([Configuring issue templates](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/configuring-issue-templates-for-your-repository), [Form schema](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/syntax-for-githubs-form-schema)). Confirm PyYAML (or equivalent) is already available to pytest in the engine env before writing yaml.safe_load tests; if absent, assert via stdlib-only structure checks or the existing JSON-style packaging pattern without adding a dependency.

## Dependencies

- GitHub issue forms / PR template support (platform)
- Existing `repo_root` fixture in `skills/sr-search/tests/conftest.py`
- `CONTRIBUTING.md` + troubleshooting/torch docs URLs (link targets)

## Challenges & Mitigations

- **PyYAML not a direct engine dep**: It is locked transitively via `sentence-transformers` → `huggingface-hub`. Use `yaml.safe_load` in tests (present under `make sync`); do **not** add a direct dependency for this.
- **Over-long bug form scares humans**: Cap fields to the list above; short labels; optional for non-load-bearing; do not require pre-submit checkboxes.
- **Component-split temptation later**: Area dropdown is the escape hatch; revisit separate forms only if filed bugs show a field set that repeatedly diverges.
- **PR template deleted wholesale**: Keep under ~15 lines of checklist; put rare Niko note in HTML comment.

## Pre-Mortem

- **Plan failed because templates omitted doctor / conventional-commit consequence in the name of brevity**: ADHD-short means wording, not field deletion — pin both in tests (doctor required field; PR template substring).
- **Plan failed by shipping 5 component bug forms nobody fills**: already covered — single form + Area dropdown.
- **Plan failed because tests lived outside `make test` path**: already covered — engine `tests/` + `repo_root`.
- **Plan failed: blank issues accidentally disabled**: pin `blank_issues_enabled: true` in test.

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Pre-Mortem complete
- [x] Preflight
- [x] Build
- [ ] QA

## Preflight Amendments

- Added Troubleshooting `contact_links` entry in `config.yml` (keeps blanks open; reduces RTM filings).
- Added `title` prefixes `[Bug]: ` / `[Feature]: ` on issue forms.
- Clarified PyYAML: transitive via huggingface-hub; no new direct dep.
