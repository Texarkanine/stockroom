# Task: p5-m1-install-docs

* Task ID: p5-m1-install-docs
* Complexity: Level 2
* Type: Simple enhancement

Author user-facing install and usage documentation covering marketplace-add and manual-install paths; empirically verify and document per-harness skill invocation forms (`/sr-*` in Cursor vs Claude Code's `<plugin>:<skill>`); confirm existing dual manifests support manual install; add a packaging/doc contract test that pins documented skill names and invocation forms to the `skills/` tree so the install guide cannot drift.

## Test Plan (TDD)

### Behaviors to Verify

- [Skill inventory pin]: discover directories under `skills/*/SKILL.md` with YAML `name:` → each name appears in the install/usage doc
- [Cursor invocation pin]: install/usage doc documents Cursor form `/<skill-name>` for every shipped skill (e.g. `/sr-search`)
- [Claude invocation pin]: install/usage doc documents Claude Code form `stockroom:<skill-name>` (or the empirically confirmed equivalent) for every shipped skill
- [No phantom skills]: every skill name cited in the install/usage doc's skill inventory / invocation tables exists as `skills/<name>/SKILL.md`
- [Status freshness]: README status line no longer claims "Phase 4 in progress"
- [Regression]: existing `test_packaging.py` / `test_skill_hygiene.py` contracts still pass

### Edge Cases

- [Extra skill dir without SKILL.md]: ignored by discovery (same spirit as packaging tests that only read real skills)
- [Dev-only mirror]: `.cursor/skills/stockroom-local/` is not part of the install payload and must not be required by the contract
- [Niko / shared skills]: `.cursor/skills/shared/**` must not appear in the install doc inventory

### Test Infrastructure

- Framework: pytest (`skills/sr-search/pyproject.toml` `[tool.pytest.ini_options]`)
- Test location: `skills/sr-search/tests/`
- Conventions: `test_*.py`; packaging contracts use `repo_root` fixture from `conftest.py`; Phase-4 precedent is `test_planning_docs_use_dashboard_port_6767` in `test_packaging.py`
- New test files: none — extend `skills/sr-search/tests/test_packaging.py` with one (or a small cluster of) install-doc contract test(s)

## Implementation Plan

1. **Failing packaging/doc contract** — add test(s) in `test_packaging.py` that read `README.md` at repo root, discover shipped skill names via existing `_front_matter` on each `skills/*/SKILL.md`, and assert for every name `N`: README contains Cursor form `/N` and Claude form `stockroom:N`; assert README does not contain `Phase 4 in progress`; assert every skill name cited in a delimited inventory block (or equivalent pinned list) is a real shipped skill. Run → expect fail (doc gaps).
   - Files: `skills/sr-search/tests/test_packaging.py`
   - Changes: new test function(s); reuse `_front_matter` (do not duplicate YAML parsing); discovery helper for `skills/*/SKILL.md` names only

2. **Install & usage documentation** — author user-facing install/usage content in `README.md` (primary surface; no new docs site). Cover: (a) marketplace-add path pointing at `https://github.com/Texarkanine/txrk9-agent-plugins` then install `stockroom`; (b) manual-install path via existing dual manifests (committed layout = install layout; point at `.cursor-plugin/` / `.claude-plugin/` + shared `skills/`); (c) post-install first step `sr-initialize`; (d) skill inventory and per-harness invocation forms for all five skills; (e) brief usage pointers to the four surfaces after init. Follow slobac's `using-slobac.md` shape (marketplace → install → invoke) adapted for multi-skill stockroom. Refresh status line to reflect Phase 5 / shipping posture (honest: marketplace entry is m2 — say install docs + manual path are ready; marketplace publication follows).
   - Files: `README.md`
   - Changes: replace stale Phase-4 status; add Install & Usage section(s); keep existing torch/dev sections intact below or clearly separated as contributor-facing

3. **Empirical invocation verification** — with operator, confirm Cursor `/sr-*` and Claude Code `stockroom:<skill>` (or actual observed form) in live sessions against a manually installed or localdev plugin; update README wording to match observed forms exactly; re-run contract tests.
   - Files: `README.md` (wording only if forms differ from plan assumptions); `memory-bank/active/progress.md` / `activeContext.md` (record verified forms)
   - Changes: document verified forms; no engine code changes expected

4. **Manual-install smoke (docs fidelity)** — walk the documented manual-install steps against the existing dual manifests (no manifest edits unless a real gap is found); fix docs if steps are wrong. Manifests already pass `test_packaging.py` — this step is confirmation, not greenfield scaffolding.
   - Files: possibly none; only touch manifests if a real install blocker is found (unlikely)
   - Changes: doc corrections if needed

5. **Green suite** — re-run new contract tests + full `make test` / relevant packaging suite; fix any drift.
   - Files: as needed from failures
   - Changes: minimal

## Technology Validation

No new technology - validation not required

## Dependencies

- Existing dual manifests (`.cursor-plugin/plugin.json`, `.claude-plugin/plugin.json`) and `skills/` tree — already in repo from Phase 0
- slobac install-doc shape (`../slobac/skills/slobac-audit/references/docs/using-slobac.md`) as reference, not a runtime dependency
- Operator availability for live Cursor + Claude Code invocation checks (cannot be fully automated in CI)
- Marketplace publication is **out of scope** (m2); docs may describe the marketplace path as the intended install once m2 lands, and must still document a working manual path now

## Challenges & Mitigations

- **Empirical forms need live harnesses**: Mitigation — plan assumes Cursor `/sr-<name>` and Claude `stockroom:<skill-name>` from roadmap + slobac archive; build step 3 is an explicit operator checkpoint; contract test pins whatever the README states after verification
- **README dual audience (users vs contributors)**: Mitigation — put Install & Usage above Development; keep torch/Makefile content as contributor section; avoid burying install under torch-safe run contract
- **Status honesty before m2 marketplace**: Mitigation — status/docs must not claim marketplace install works until m2; phrase marketplace path as "once listed in txrk9-agent-plugins" or equivalent, with manual install as the verified path for m1
- **Roadmap checkbox wording still says "manifests added"**: Mitigation — m1 docs/verification only; do not rewrite roadmap Phase 5 bullets beyond what's needed for honesty (optional one-line status in README is enough); roadmap checkbox completion is an L4 concern at archive

## Preflight amendments

- Reuse existing `_front_matter` in `test_packaging.py`; do not add a parallel YAML parser.
- Contract pins exact substrings `/<name>` and `stockroom:<name>` in `README.md` (plus absence of `Phase 4 in progress`).

## Advisory findings (non-blocking)

- **Empirical verification is operator-gated**: step 3 cannot finish in CI; build should land docs + green contract against the planned forms, then pause for operator confirmation before claiming forms are empirically verified (or record verification evidence in progress if operator confirms mid-build).
- **Marketplace honesty**: until m2, README must not imply marketplace install already works; phrase as forthcoming / once listed.

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Preflight
- [ ] Build
- [ ] QA
