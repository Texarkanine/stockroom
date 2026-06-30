# Active Context

## Current Task: `sr-query` skill (p2-embeddings-search m4)
**Phase:** REFLECT COMPLETE

## Reflection Outcome
- Reflection written to `reflection/reflection-p2-embeddings-search-m4.md`. Clean execution; the 7-step plan was accurate and the preflight introspection-first amendment paid off. The one real surprise was a repo-wide broken invocation contract, caught by the plan's own "verify examples live" mitigation.
- Reconciled persistent/root docs (the cluster QA routed here): fixed the incomplete invocation contract in `systemPatterns.md` ("Cross-skill resource resolution" — added `PYTHONPATH="$APP_DIR/src"` + `--no-config` and a load-bearing note) and the root `README.md` (all three ad-hoc invocations); updated `techContext.md` "Query (`sr-query`)" — the wrapper skill now exists (Phase-2 m4), only per-harness invocation-form verification remains Phase 5. `productContext.md` unaffected.
- Standing insight for `sr-semantic`/`sr-search`: the run incantation is copy-pasted prose in N places (which is how it drifted into being wrong in N places); a single shared launcher (or `[project.scripts]`) is the obvious consolidation, and `sr-search` (which delegates to siblings) is the natural place to force it.

## Build Outcome
- Authored `skills/sr-query/SKILL.md` (new): front-matter `name: sr-query`, model-invocable (`enable-model-invocation: true`), license mirrors `sr-search`. Sections: when-to-use (routing vs. `sr-semantic`/`sr-search`), the verified invocation contract, `--format`/`--detail` output discipline, guardrails (context-blowout, read-only, heterogeneous `tool_input` JSON, error handling without thrashing), introspection-first schema map (labelled "as of migrations 0001–0003"), and verified worked examples.
- Edited `skills/sr-search/SKILL.md`: corrected its engine-invocation block to the working form.
- Full gate `make ci` green: **266 passed, 2 skipped** (torch-gated), ruff lint+format clean, lock-check clean, REUSE compliant (178/178 — the new SKILL.md resolves via the `skills/**` glob). Restored out-of-band torch with `make torch` after the CI sync stripped it.

## Files Modified
- `/home/mobaxterm/git/stockroom/skills/sr-query/SKILL.md` (new)
- `/home/mobaxterm/git/stockroom/skills/sr-search/SKILL.md` (invocation-block fix)

## Key Decisions & Deviations (this session)
- **Discovery → corrected the invocation contract.** The contract documented in `sr-search/SKILL.md`, `systemPatterns.md`, and the root README (`uv run --project … --no-sync python -m stockroom.<entrypoint>`) is **incomplete**: the engine is `[tool.uv] package = false`, so `stockroom` is not on `sys.path` and a bare `python -m` fails with `ModuleNotFoundError`. The working form requires **`PYTHONPATH="$APP_DIR/src"`** (and `--no-config` for hermeticity). Verified empirically against the live warehouse. The new skill ships the corrected form; I also fixed the sibling `sr-search/SKILL.md` block (in-scope same-file edit).
- **Deviation from plan step 7:** the plan anticipated a "Phase-5 wording" tweak to `sr-search/SKILL.md`, but that wording actually lives in `techContext.md` (routed to REFLECT); the load-bearing build edit was the invocation-contract fix instead.
- **JSON guardrail earned by testing:** naive `tool_input->>'key'` cast-errors across heterogeneous tool shapes; the skill teaches the robust `json_extract_string(tool_input, '$.key')` over a `tool_name`-filtered subquery (verified).
- **REFLECT items (persistent/root docs carrying the stale/incomplete contract):** `systemPatterns.md` "Cross-skill resource resolution" block and the root `README.md` ad-hoc invocation both omit `PYTHONPATH`; and `techContext.md` "Query (`sr-query`)" Phase-5 wording is now partly stale. Reconcile at REFLECT (lifecycle), not BUILD.

## Next Step
- m4 (`sr-query` skill) sub-run complete. Next: `/niko` to advance to the next milestone (`sr-semantic` skill); then STOP for the operator to run `/niko-archive` at project end.
