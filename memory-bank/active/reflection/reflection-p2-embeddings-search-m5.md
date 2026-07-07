---
task_id: p2-embeddings-search-m5
date: 2026-07-07
complexity_level: 2
---

# Reflection: `sr-semantic` skill (p2-embeddings-search m5)

## Summary

Authored `skills/sr-semantic/SKILL.md` — the safe LLM wrapper over the `python -m stockroom.semantic` pure-vector-search surface — with every shipped example verified live against the real warehouse. Delivered exactly to plan; `make ci` green throughout.

## Requirements vs Outcome

Every milestone requirement landed: routing guidance (meaning vs. `sr-query`'s exact lookups, ambiguity to `sr-search`), query-phrasing advice (including never hand-adding the bge prefix), `-k` / `--format` / `--detail` output discipline with the default-safe posture, and guardrails (context blowout via the `sr-query` full-text handoff, read-only, error table, relevance-is-relative, and the preflight-amended silent-staleness coverage check). Two small in-scope additions beyond the plan's letter: the stderr-noise note (model loader prints HF-hub/progress chatter while stdout stays pipe-clean — observed live) and a "re-phrase, don't repeat" guardrail. Nothing was dropped or reinterpreted.

## Plan Accuracy

The 7-step plan was accurate; steps executed in order with no reordering or splitting. The anticipated challenges mostly didn't bite: embeddings coverage was healthy (37,755 vectors), the model was already cached, and the torch-stripped-by-CI-sync challenge materialized exactly as predicted and was handled by the planned `make torch` restore. The verify-examples-live discipline (inherited from m4) again did its quiet work — this time confirming behavior rather than uncovering a repo-wide bug, which is what "the contract is now correct" looks like from the verification side.

## Build & QA Observations

The smoothest sub-run of the project so far: m4 had already debugged the invocation contract and established the structural template, so m5 was largely disciplined instantiation plus surface-specific knowledge (torch-at-query-time, score semantics, staleness). QA caught one trivial omission — the plan's example-drift mitigation asked for a source label on the output-format documentation (m4's "as of…" pattern) and the build forgot it; fixed in QA, gate re-run green.

## Insights

### Technical

- The torch-missing failure on this surface is an *unhandled traceback* (lazy `import torch` inside `BgeEncoder.__init__`), not a clean stderr form like the other error paths. Fine for a wrapper skill to document honestly, but if a future milestone touches `semantic.main()`, a caught `ModuleNotFoundError` → clean "torch not provisioned; run make torch" stderr line (exit 1) would make the error table uniform.

### Process

- Sibling-skill authoring against an established template (m4) collapses the cost of the second wrapper: virtually all iteration went into what is genuinely *different* about the surface (torch, scores, staleness), not into structure or contract. This confirms the milestone-list intuition that `sr-query`/`sr-semantic` could have merged — but also shows the split cost little.

### Million-Dollar Question

Had "wrapper skills ship alongside their surfaces" been foundational, each engine module's CLI contract (flags, exit codes, stderr forms) would have been *specified by the skill first* and implemented to match — making the skill the source of truth and the CLI its implementation, rather than the skill an after-the-fact transcription that QA must check for drift. The shipped result is materially the same here because the m3/m3.5 CLI was already agent-first by design; the ordering insight matters more for future surfaces.

