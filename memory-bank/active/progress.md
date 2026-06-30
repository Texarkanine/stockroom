# Progress

Sub-run m4 of the `p2-embeddings-search` L4 project: author the **`sr-query` skill** — a SKILL.md (+ optional helper `scripts/`) that wraps the already-built read-only SQL surface (`python -m stockroom.query`) with ergonomic, safe LLM guidance: when/how to use it, the `--format {tsv,json,table}` / `--detail {compact,snippet,full}` flags landed in m3/m3.5, and guardrails against context blowout and wasted tool calls. Per the project invariant, prompt-skill behavior is verified artisanally by the operator; the TDD rule binds only any Python helper scripts. Design is settled by `creative/creative-search-surface-architecture.md` and `planning/brainstorm/print-for-who.md` — no creative phase. No schema/migration, no new runtime dependency.

**Complexity:** Level 2

## 2026-06-30 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - L4 re-entry (Step 2a): m3.5 (Output format defaults `--format`) confirmed `REFLECT COMPLETE` and checked off in `milestones.md`; m3.5 sub-run ephemerals cleared (`tasks.md`, `activeContext.md`, `progress.md`, `.qa-validation-status`, `.preflight-status`).
    - Classified the **`sr-query` skill** milestone as **Level 2** and wrote the determination to the memory bank.
* Decisions made
    - Level 2: a self-contained, additive enhancement — author one new `sr-query` SKILL.md (+ optional helper `scripts/`) wrapping an existing module, contained to the new skill. Design is fully settled by the search-surface architecture creative doc and `print-for-who.md`, so no creative phase (which would tip it toward L3). Advisory estimate was L1/L2; the bug-fix-only L1 branch does not fit authoring a new prose skill with guardrails.
    - Preserved `creative/creative-search-surface-architecture.md` through the m3.5→m4 advance: it is the project-level decision record (referenced by `milestones.md` and `print-for-who.md`), not a sub-run artifact — consistent with the m3→m3.5 precedent.

## 2026-06-30 - PLAN - COMPLETE

* Work completed
    - Surveyed the wrapped surface (`stockroom.query` CLI flags/exit-codes/stderr forms), the `sr-search` SKILL.md front-matter + inline invocation contract, `creative-search-surface-architecture.md`, `print-for-who.md`, `REUSE.toml`, and both plugin manifests.
    - Wrote the full Level 2 plan to `tasks.md`: author `skills/sr-query/SKILL.md` as the safe LLM wrapper over `python -m stockroom.query` in 7 ordered steps (front-matter → routing → invocation contract → `--format`/`--detail` discipline → guardrails → schema map + verified examples → `sr-search` cross-ref edit).
* Decisions made
    - Prose-only — no helper `scripts/` this sub-run (resolves the milestone's "where helper scripts live" open question: future home `skills/<skill>/scripts/`, not exercised here); a bash resolver re-introduces the resolution problem and Python would drag in the TDD obligation for no gain.
    - Front-matter `enable-model-invocation: true` (live skill vs. the `sr-search` skeleton's `false`); no `plugin.json` edit (auto-discovery), no `REUSE.toml` edit (glob-covered).
    - Verification is artisanal per the project invariant (TDD binds Python only; none written here); automated gate is `make ci` green + `make reuse`.

## 2026-06-30 - PREFLIGHT - COMPLETE

* Work completed
    - Validated the plan against codebase reality: TDD-encoding (passes by exemption — prose deliverable, no Python, artisanal verification per the project invariant), convention compliance (`skills/sr-query/SKILL.md` layout, front-matter mirroring `sr-search` with `enable-model-invocation: true`, glob-covered REUSE, plugin auto-discovery), dependency impact, conflict detection (no duplication; wraps not reimplements), completeness (every milestone requirement mapped). Result: PASS.
* Decisions made
    - Applied one in-scope amendment: step 6 leads with a live schema-introspection query and labels the static column map "as of migrations 0001–0003", making the skill self-maintaining across future migrations and structurally discharging the example-drift challenge.
* Insights
    - Advisory routed to REFLECT (m3.5 precedent, not a build task): `techContext.md` "Query (`sr-query`)" Phase-5 wording goes partly stale once the wrapper ships; the identical "Semantic search" Phase-5 line is reconciled when `sr-semantic` lands next.

## 2026-06-30 - BUILD - COMPLETE

* Work completed
    - Authored `skills/sr-query/SKILL.md` (the wrapper deliverable) and fixed the engine-invocation block in the sibling `skills/sr-search/SKILL.md`. Verified every shipped example query + the introspection query against the live warehouse before writing them in.
    - Full `make ci` green: 266 passed, 2 skipped (torch-gated), ruff lint+format clean, lock-check clean, REUSE 178/178 (new SKILL.md covered by the `skills/**` glob). Restored out-of-band torch via `make torch` after the CI sync stripped it.
* Decisions made
    - Corrected a real, repo-wide doc bug: the engine invocation contract (in `sr-search/SKILL.md`, `systemPatterns.md`, README) omits `PYTHONPATH="$APP_DIR/src"`, so a bare `python -m stockroom.query` fails (`package = false` ⇒ not on `sys.path`). The skill ships the verified working form (`PYTHONPATH` + `--no-config`); fixed the sibling SKILL.md too.
    - Earned a JSON guardrail from testing: naive `tool_input->>'key'` cast-errors across heterogeneous tool shapes → teach `json_extract_string` over a `tool_name`-filtered subquery.
* Insights
    - REFLECT must reconcile the incomplete invocation contract in `systemPatterns.md` ("Cross-skill resource resolution") and the root `README.md`, plus the partly-stale `techContext.md` Query Phase-5 wording. The build edit was scoped to the shipped skill payloads; persistent/root-doc reconciliation is REFLECT work per the lifecycle.

## 2026-06-30 - QA - COMPLETE

* Work completed
    - Semantic review (KISS/DRY/YAGNI/completeness/regression/integrity/documentation) of `sr-query/SKILL.md` + the `sr-search/SKILL.md` edit against the plan. Result: PASS, no trivial fixes required.
* Decisions made
    - Confirmed the deliverable's accuracy against ground truth (truncate budgets, stderr forms/exit codes, JSON shape, schema DDL) — all examples were executed live during build. The repeated invocation prefix is intentional copy-paste ergonomics, not a DRY defect.
    - Confirmed the persistent/root-doc reconciliation (the incomplete invocation contract in `systemPatterns.md`/README; stale `techContext.md` Query Phase-5 wording) is a REFLECT responsibility per the lifecycle (m3.5 precedent), not a QA-blocking documentation gap — the shipped skill payloads themselves are correct and updated.
