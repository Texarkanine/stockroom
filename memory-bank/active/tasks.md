# Task: Wrapper-skill trimming pass

* Task ID: p3-m5-wrapper-skill-trimming
* Complexity: Level 2
* Type: simple enhancement (bounded editing pass + one small engine message fix)

Swap every invocation incantation for `stockroom <subcommand>` across `sr-query` / `sr-semantic` / `sr-search`, apply the litter-audit inventory (`planning/brainstorm/skill-litter-audit.md`: Categories A–C out, D kept), create the shared system-model reference doc, add one shared-doc pointer per skill, and re-run the m6 grep-verifiable no-invocation-token check. One in-scope engine amendment: the missing-warehouse stderr hint in `query`/`semantic`/`embed` still advises ``run `python -m stockroom.ingest` first`` — a raw module invocation that no longer works bare and that the skills' error tables quote verbatim; it becomes ``run `stockroom ingest` first``.

## Test Plan (TDD)

### Behaviors to Verify

Engine (TDD, pytest):

- B1: `stockroom.query` CLI with no warehouse present → exit 1, stderr message ends ``run `stockroom ingest` first`` (pinned exactly, per the m4 pin-the-whole-string lesson — the current tests only assert `"ingest" in stderr`)
- B2: `stockroom.semantic` CLI with no warehouse present → same exact hint, encoder never constructed (existing seam)
- B3: `stockroom.embed` CLI with no warehouse present → same exact hint, encoder never constructed

Prose (artisanal verification + mechanical check, per the project invariant):

- B4: `skills/sr-search/references/system-model.md` exists and holds the *why* content (torch contract, run-in-place packaging, ETL / read-only-by-construction, no-truncation-at-rest doctrine, embedding pipeline & staleness model, identity/provenance philosophy) with **no operational incantations** — the doc holds why, skills hold do
- B5: all three wrapper SKILL.md files invoke only `stockroom <subcommand>`; the failure path is exactly "`command -v stockroom` fails → run `sr-initialize`" with **no fallback incantation**
- B6: each of the three skills carries exactly one pointer to the shared doc (sibling-relative, e.g. `../sr-search/references/system-model.md` — committed layout = install layout)
- B7: the m6 no-invocation-token check across all three wrapper SKILL.md files finds zero hits for `APP_DIR`, `PYTHONPATH`, `uv run`, `--no-sync`, `--no-config`, `CURSOR_PLUGIN_ROOT`, `find -L`, `python -m stockroom` — encoded as a permanent pytest (`tests/test_skill_hygiene.py`, preflight amendment) so the invariant is regression-pinned in CI, not a one-shot manual grep
- B8: every shipped example in the trimmed skills is executed live against the real warehouse before being written in

### Test Infrastructure

- Framework: pytest, invoked via `make test` / `make ci` from the repo root
- Test location: `skills/sr-search/tests/`
- Conventions: CLI behavior tested via subprocess or `main([])` with env-pointed `STOCKROOM_HOME`; friendly-error tests already exist for all three surfaces
- New test files: `tests/test_skill_hygiene.py` (B7 — repo-root-relative SKILL.md scan, same `repo_root` convention as `test_packaging.py`); tighten `test_query_cli.py::test_query_missing_warehouse_is_friendly`, `test_semantic.py::test_cli_missing_warehouse_is_friendly`, `test_embed.py::test_embed_cli_missing_warehouse_is_friendly`

## Implementation Plan

1. [x] Engine hint swap (TDD cycle)
   - Files: `skills/sr-search/tests/test_query_cli.py`, `tests/test_semantic.py`, `tests/test_embed.py`, then `src/stockroom/query.py`, `src/stockroom/semantic.py`, `src/stockroom/embed.py`
   - Changes: tighten the three missing-warehouse tests to pin the exact new message tail (red), then change the three `print(...)` hints to ``run `stockroom ingest` first`` (green)
2. [x] Skill-hygiene test (TDD cycle spanning the prose steps)
   - Files: `skills/sr-search/tests/test_skill_hygiene.py` (new)
   - Changes: for each of the three wrapper SKILL.md files, assert zero occurrences of the B7 token set (word-boundary-aware where needed — e.g. `python -m stockroom` must also catch `python -m stockroom.query`). Written *now* so it is red against the untrimmed skills; steps 3–5 drive it green — the grep check becomes the failing test that drives the prose edit
3. [x] Author the shared system-model reference doc
   - Files: `skills/sr-search/references/system-model.md` (new)
   - Changes: Category A/B content from the litter audit — torch contract (out of lock, out-of-band provisioning, why `--no-sync` exists), run-in-place packaging (`[tool.uv] package = false`, why the shim exists), ETL / read-only-by-construction, no-truncation-at-rest doctrine, embedding pipeline + staleness model, identity/provenance philosophy (`source_*` demotion). No operational rules — those stay in skills. REUSE: PPL-S applies automatically via the `skills/**` glob (`.md` is not code-shaped); verify with `make reuse`
4. [x] Trim `skills/sr-query/SKILL.md`
   - Files: `skills/sr-query/SKILL.md`
   - Changes: invocation section collapses to `stockroom query …` + the `command -v stockroom` → `sr-initialize` failure path; all examples/guardrails/worked-example prefixes swap to `stockroom query`; Category A cuts (rationale bullets, "rebuildable ETL output", planner theory, provenance framing); Category B (flag-bullet triplet gone with the incantation); Category C (self-description padding, "Two independent axes" narration); Category D kept (error table — quoting the *new* engine hint, `tool_input` JSON guardrail, schema map, identity join rule); one shared-doc pointer added; every example executed live before write-in
5. [x] Trim `skills/sr-semantic/SKILL.md`
   - Files: `skills/sr-semantic/SKILL.md`
   - Changes: same treatment; the full-text-handoff and coverage-check examples become `stockroom query …`; torch-missing advice collapses to the single error-table row with next-action "re-run `sr-initialize`" (litter audit B: the duplicate runtime-notes paragraph goes); `--format` lead-in maintenance metadata moves out (Category C); score semantics, staleness guardrail, re-phrase-don't-repeat, prefix-doubling warning all kept (Category D); one shared-doc pointer; every example executed live
6. [x] Touch up `skills/sr-search/SKILL.md`
   - Files: `skills/sr-search/SKILL.md`
   - Changes: already zero invocation plumbing (m6 verified); add the one shared-doc pointer (fold into the engine-home breadcrumb), confirm no Category C narration crept in; steps 4–6 together drive the step-2 hygiene test green
7. [x] Reconcile persistent docs
   - Files: `memory-bank/systemPatterns.md` (the "Cross-skill resource resolution" section still teaches the pre-shim `$APP_DIR`/`PYTHONPATH` contract as the skill-facing pattern — rewrite around "the shim owns the contract; skills say `stockroom <subcommand>`"), `memory-bank/techContext.md` (the line-133 quote of the old hint and any skill-invocation mentions updated; the `stockroom.query`/`semantic` sections gain nothing new), `README.md` (verify only — the dev-facing raw incantation in the shim section is the shim's own documentation, not skill litter)
   - Changes: post-shim contract described once; the raw incantation survives only where it documents the shim/dev internals
8. [x] Verification
   - Files: none (checks)
   - Changes: full test suite (includes the new hygiene test and the three tightened hint tests); full `make ci` (test, lint, format-check, lock-check, reuse — REUSE covers the two new files via existing globs); live example execution happens during steps 4–5 (before the final CI gate); re-provision torch (`make torch`) if a `make` target ran between provisioning and a torch-needing live example (m4 insight: exact sync strips torch every run)

## Technology Validation

No new technology - validation not required.

## Dependencies

- The m2 shim is live on this machine (`command -v stockroom` succeeds) — required for B8 live example execution
- Populated warehouse (809 sessions / 29 080 messages / 39 805 vectors from the m4 first run) — required for realistic live examples
- Torch provisioned for the `sr-semantic` live examples (`make torch` if stripped)

## Challenges & Mitigations

- Torch stripped by `make ci` between example runs: sequence live example execution *before* the final CI gate, or re-run `make torch` after; the nightly job is immune but the dev box is not
- The exact-message pin (B1–B3) must match all three modules byte-for-byte: assert one shared expected string in each test rather than three hand-typed variants drifting
- Over-trimming risk (cutting Category D recognition/recovery content): the litter audit's Category D list is the keep-list; diff review against it before committing
- The shared doc restating operational rules would reintroduce the drift problem with a second head (audit's explicit warning): the doc gets *why* only; any "always pass X" phrasing is a smell caught in QA

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Preflight
- [x] Build
- [ ] QA
