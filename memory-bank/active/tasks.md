# Task: dependabot-config

* Task ID: dependabot-config
* Complexity: Level 2
* Type: simple enhancement

Add `.github/dependabot.yaml` for UV docs (`/`), UV engine (`/skills/sr-search`), and GitHub Actions, using the major-isolation / minor+patch grouping pattern from `a16n` and `inquirerjs-checkbox-search`, with UV cooldown 7 days, GHA no grouping and cooldown opted out (`default-days: 0`), and the four commit prefixes from the brief.

## Test Plan (TDD)

### Behaviors to Verify

- File exists: repo has `.github/dependabot.yaml` → parses as YAML with `version: 2` and a non-empty `updates` list
- Three ecosystems: `updates` contains exactly one `uv` entry for `/`, one `uv` entry for `/skills/sr-search`, and one `github-actions` entry for `/` (no npm)
- UV major isolation: each UV entry's `groups` only list `update-types: [minor, patch]` (no `major` in any group) → majors stay ungrouped / separate PRs
- UV cooldown: each UV entry has `cooldown.default-days: 7`
- GHA no grouping: the `github-actions` entry has no `groups` key
- GHA no cooldown: the `github-actions` entry has `cooldown.default-days: 0` (explicit opt-out of Dependabot's platform default 3-day cooldown; see [GitHub changelog 2026-07-14](https://github.blog/changelog/2026-07-14-dependabot-version-updates-introduce-default-package-cooldown/))
- Commit prefixes:
  - docs UV (`directory: /`): `commit-message.prefix` is `chore(docs)`
  - engine UV: `prefix` is `fix(deps)`, `prefix-development` is `chore(deps-dev)`
  - GHA: `prefix` is `chore(deps-ci)`
- Engine grouping split: engine UV has separate production and development minor+patch groups (mirrors reference npm pattern)
- Edge: empty/malformed file would fail parse assertions; missing required keys fail existence assertions (contract style, same family as `test_packaging.py`)

### Test Infrastructure

- Framework: pytest (engine suite under `skills/sr-search/`)
- Test location: `skills/sr-search/tests/`
- Conventions: repo-root contract tests use the `repo_root` fixture (`conftest.py`); packaging-style structural assertions in dedicated `test_*.py` modules (see `test_packaging.py`)
- New test files: `skills/sr-search/tests/test_dependabot.py`
- Parser: `yaml` (PyYAML already present in the engine env as a transitive of `transformers` / `huggingface-hub`; importable via `uv run`)

## Implementation Plan

1. **Stub contract tests (empty bodies)**
   - Files: `skills/sr-search/tests/test_dependabot.py`
   - Changes: Add module docstring + test function stubs covering the behaviors above (no assertions yet beyond placeholders / `pass`)

2. **Implement failing contract tests**
   - Files: `skills/sr-search/tests/test_dependabot.py`
   - Changes: Load `.github/dependabot.yaml` via `repo_root`, parse with `yaml.safe_load`, assert ecosystems, directories, groups, cooldowns, and commit-message prefixes as listed in Test Plan. Run tests — expect FAIL (file missing).

3. **Add Dependabot config to satisfy tests**
   - Files: `.github/dependabot.yaml` (new)
   - Changes: Create version-2 config with three `updates` entries:
     - `uv` + `directory: '/'` — groups minor+patch only; `cooldown.default-days: 7`; `commit-message.prefix: chore(docs)`; also set `prefix-development: chore(docs)` so dependency-group packages still get the docs prefix if Dependabot classifies them as development
     - `uv` + `directory: '/skills/sr-search'` — production + development minor+patch groups; `cooldown.default-days: 7`; `prefix: fix(deps)` / `prefix-development: chore(deps-dev)`
     - `github-actions` + `directory: '/'` — **no** `groups`; `cooldown.default-days: 0`; `prefix: chore(deps-ci)`
     - Match reference-repo conveniences that do not conflict with the brief: monthly Monday 09:00 schedule, `assignees: [Texarkanine]`, open-PR limits 10 (uv) / 5 (gha)
   - Run tests — expect PASS

4. **Verification**
   - Files: none new
   - Changes: Run the new test module, then full `make test` (or project-equivalent) before declaring build done

5. **Documentation**
   - No contributor/user-guide mention of Dependabot exists today; brief does not require docs. Skip unless preflight/advisory finds a natural one-line home — default: no doc change.

## Technology Validation

No new technology — validation not required. Dependabot `uv` ecosystem and `cooldown` are platform-supported ([Dependabot options reference](https://docs.github.com/en/code-security/dependabot/dependabot-version-updates/configuration-options-for-the-dependabot.yml-file)).

## Dependencies

- Existing: pytest, PyYAML (transitive, already importable in engine env)
- Reference configs: `/home/mobaxterm/git/a16n/.github/dependabot.yaml`, `/home/mobaxterm/git/inquirerjs-checkbox-search/.github/dependabot.yaml`, `/home/mobaxterm/git/jekyll-highlight-cards/.github/dependabot.yaml` (prefix style)

## Challenges & Mitigations

- **Docs UV deps live in `[dependency-groups]` not `[project].dependencies`**: Dependabot may treat them as development → set both `prefix` and `prefix-development` to `chore(docs)`.
- **Platform default 3-day cooldown**: Omitting `cooldown` on GHA no longer means "no cooldown" → set `default-days: 0` explicitly.
- **`default-days: 0` vs docs saying 1–90**: Changelog documents opt-out; if GitHub rejects `0` at runtime, fall back to documenting the closest supported opt-out and reopen with operator — plan assumes `0` per changelog.
- **Transitive PyYAML in tests**: Acceptable while `transformers` remains a runtime dep; if import ever fails, promote `pyyaml` to the engine `dev` group (out of brief scope unless it bites).

## Pre-Mortem

- **Wrong UV directories (e.g. treating `docs/` as a uv root)**: already covered by Challenge on roots — plan pins `/` and `/skills/sr-search` from `pyproject.toml` + `uv.lock` locations.
- **GHA still delayed 3 days because cooldown block omitted**: already covered by Challenge on platform default.
- **Commit prefixes wrong because `include: scope` double-scopes** (e.g. `fix(deps)(deps)`): plan deliberately omits `include: scope` and embeds the full conventional prefix strings, matching `jekyll-highlight-cards`.
- **Tests green but Dependabot ignores config filename**: GitHub accepts `dependabot.yml` and `dependabot.yaml`; brief asks for `.yaml` — keep `.yaml`.

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Pre-Mortem complete
- [ ] Preflight
- [ ] Build
- [ ] QA
