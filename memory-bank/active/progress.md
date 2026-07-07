# Progress

Sub-run m5 of the `p2-embeddings-search` L4 project: author the **`sr-semantic` skill** — a SKILL.md (+ optional helper `scripts/`) that wraps the already-built pure vector-search surface (`python -m stockroom.semantic`) with ergonomic, safe LLM guidance: when/how to use it (routing vs. `sr-query`/`sr-search`), query phrasing, `-k`, the `--format {tsv,json,table}` / `--detail {compact,snippet,full}` flags, and guardrails against context blowout and wasted tool calls. Same default-safe / full-detail / user-facing format guidance as the `sr-query` skill (m4). Per the project invariant, prompt-skill behavior is verified artisanally by the operator; the TDD rule binds only any Python helper scripts. Design is settled by `creative/creative-search-surface-architecture.md` and `planning/brainstorm/print-for-who.md` — no creative phase. No schema/migration, no new runtime dependency.

**Complexity:** Level 2

## 2026-07-07 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - L4 re-entry (Step 2a): m4 (`sr-query` skill) confirmed `REFLECT COMPLETE` and checked off in `milestones.md`; m4 sub-run ephemerals cleared (`tasks.md`, `activeContext.md`, `progress.md`, `.qa-validation-status`, `.preflight-status`).
    - Classified the **`sr-semantic` skill** milestone as **Level 2** and wrote the determination to the memory bank.
* Decisions made
    - Level 2: a self-contained, additive enhancement — author one new `sr-semantic` SKILL.md (+ optional helper `scripts/`) wrapping an existing module, contained to the new skill. Design is fully settled by the search-surface architecture creative doc and `print-for-who.md`, so no creative phase. Structurally identical to the m4 (`sr-query`) sub-run, which was Level 2; the bug-fix-only L1 branch does not fit authoring a new prose skill with guardrails.
    - Preserved `creative/creative-search-surface-architecture.md` through the m4→m5 advance: it is the project-level decision record (referenced by `milestones.md` and `print-for-who.md`), not a sub-run artifact — consistent with the m3→m3.5 and m3.5→m4 precedents.
* Insights
    - Standing insight from the m4 reflection to carry into this sub-run: the engine run incantation (`PYTHONPATH="$APP_DIR/src"` + `--no-config` + `uv run --project … --no-sync`) is copy-pasted prose in N places and drifted into being wrong before m4 fixed it repo-wide; this skill will re-paste the same preamble, and a shared launcher (or `[project.scripts]`) remains the obvious consolidation to force at the `sr-search` milestone.

## 2026-07-07 - PLAN - COMPLETE

* Work completed
    - Surveyed the wrapped surface (`stockroom.semantic` CLI flags/exit-codes/stderr forms; `render.format_semantic` output columns per format), the m4 `sr-query` SKILL.md as structural template, `systemPatterns.md` (invocation contract, semantic-search pattern), and `techContext.md`.
    - Wrote the full Level 2 plan to `tasks.md`: author `skills/sr-semantic/SKILL.md` as the safe LLM wrapper over `python -m stockroom.semantic` in 7 ordered steps (front-matter → routing/query-phrasing → invocation contract → output discipline → guardrails → verified examples → integration checks + gate).
* Decisions made
    - Prose-only — no helper `scripts/`, no Python (m4 precedent); TDD passes by project-invariant exemption; verification is artisanal (every shipped example executed live first) + `make ci` green.
    - Canonical full-text fetch for a semantic hit is a handoff to `sr-query` by `message_id` (json carries the ids) — skill composability over duplicating a fetch surface.
    - Surface-specific torch guardrail: `stockroom.semantic` needs torch at query time; torch-missing is an environment problem (`make torch`), never a retry loop.
    - No `sr-search/SKILL.md` / `plugin.json` / `REUSE.toml` edits expected (m4-corrected invocation block already in place; skill auto-discovery; REUSE glob coverage).
* Insights
    - `techContext.md` "Semantic search" Phase-5 wording goes partly stale once this wrapper ships — route to REFLECT (m4 precedent), not a build task.

## 2026-07-07 - PREFLIGHT - COMPLETE

* Work completed
    - Validated the plan against codebase reality: TDD-encoding (passes by exemption — prose deliverable, no Python, artisanal verification per the project invariant; each verified behavior enumerated per-unit in the test plan), convention compliance (`skills/sr-semantic/SKILL.md` layout beside `sr-query`; front-matter mirrors the m4 template with `enable-model-invocation: true`; REUSE covered by the `skills/**` glob; `.cursor-plugin/plugin.json` auto-discovers `./skills/`), dependency impact (no Python → no test surface; `sr-search/SKILL.md` already lists the `stockroom.semantic` entrypoint post-m4 fix; `make localdev` re-run planned in step 7), conflict detection (no existing `sr-semantic` skill; wraps, not reimplements), completeness (every milestone requirement — routing, query phrasing, `-k`, `--format`/`--detail`, guardrails, default-safe/full-detail/user-facing format guidance — mapped to a concrete plan step). Result: PASS.
* Decisions made
    - Applied one in-scope amendment: plan step 5 gains guardrail (e) *silent-staleness* — semantic search only sees embedded content, so weak results for recent work signal an embeddings-coverage lag (check via the `sr-query` handoff; suggest incremental `python -m stockroom.embed`) rather than absence — closing the one failure mode the plan's guardrails didn't cover.
* Insights
    - The shared-launcher consolidation from the m4 reflection remains deliberately deferred to the `sr-search` milestone (which delegates to both siblings and is the natural forcing point); pulling it forward would expand this sub-run's scope for no m5 payoff.

## 2026-07-07 - BUILD - COMPLETE

* Work completed
    - Authored `skills/sr-semantic/SKILL.md` (the wrapper deliverable) per the 7-step plan: front-matter, routing/query-phrasing, invocation contract (with the torch-at-query-time caveat), `-k`/`--format`/`--detail` output discipline, guardrails (incl. the preflight-amended silent-staleness check and the `sr-query` full-text handoff), verified worked examples, relaying-to-a-human.
    - Verified every shipped example live against the real warehouse before writing it in (default call, `-k`, json, table/compact, both exit-2 error paths, the handoff pair, the coverage query; 37,755 embeddings at verification time). Confirmed `sr-search/SKILL.md`, `plugin.json`, `REUSE.toml` need no edits; re-ran `make localdev`.
    - Full `make ci` green: 266 passed, 2 skipped, ruff lint+format clean, lock-check clean, REUSE 180/180. Restored torch via `make torch` after the CI sync stripped it and re-verified a live semantic call (m4 precedent, anticipated by the plan).
* Decisions made
    - Built to plan, no deviations. One in-scope addition (plan step 3's territory): documented that model loading emits HF-hub/progress noise to stderr while stdout stays pipe-clean — observed live; prevents an agent misreading loader noise as an error.
* Insights
    - REFLECT must reconcile the `techContext.md` "Semantic search" Phase-5 wording (the wrapper now exists; only per-harness invocation-form verification remains Phase 5) — flagged since PLAN, m4 precedent.

## 2026-07-07 - QA - COMPLETE

* Work completed
    - Semantic review (KISS/DRY/YAGNI/completeness/regression/integrity/documentation) of `skills/sr-semantic/SKILL.md` against the plan. Result: PASS with one trivial fix applied directly: the plan's example-drift mitigation called for labeling the output-column documentation with its source (m4's "as of…" pattern), which the build omitted — added the `stockroom.render` source label to the `--format` section. `make ci` re-run green (266 passed, 2 skipped, REUSE 180/180); torch restored via `make torch`.
* Decisions made
    - Confirmed the deliverable's accuracy against ground truth: every example, error form, exit code, output shape, and the coverage query were executed live during build. The repeated invocation preamble across examples is intentional copy-paste ergonomics (m4 QA precedent), not a DRY defect; the twice-appearing `sr-query` handoff command (guardrail + example) is teach-then-demonstrate, also intentional.
    - Torch-missing row in the error table deliberately carries no clean exit code ("—"): the failure surfaces as an unhandled traceback (lazy import in `BgeEncoder`), and the dash honestly signals it is not a handled-error form.
    - Confirmed no README update owed (README documents the engine + dev entrypoints, not the skill roster); `techContext.md` "Semantic search" Phase-5 wording remains REFLECT work per the lifecycle (m4 precedent).
