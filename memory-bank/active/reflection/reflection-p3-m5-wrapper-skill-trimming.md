---
task_id: p3-m5-wrapper-skill-trimming
date: 2026-07-09
complexity_level: 2
---

# Reflection: Wrapper-skill trimming pass

## Summary

Trimmed all three wrapper skills to the `stockroom <subcommand>` contract, moved the system-model *why* into one shared reference doc (`skills/sr-search/references/system-model.md`), and promoted the m6 no-invocation-token grep check into a permanent pytest. Both trimmed skills lost roughly a third of their prose with zero operational loss; every shipped example was live-executed first; `make ci` green (365 passed) and QA passed with no findings.

## Requirements vs Outcome

Every milestone requirement delivered: incantation swap across `sr-query` / `sr-semantic` / `sr-search`, the litter-audit inventory applied (Categories A–C out, D kept), the shared doc created, one pointer per skill, and the no-invocation-token check re-run — now as `test_skill_hygiene.py` rather than a one-shot grep, the preflight amendment. One small in-scope addition the plan itself introduced: the engine's missing-warehouse hint (`query`/`semantic`/`embed`) was updated from ``run `python -m stockroom.ingest` first`` to ``run `stockroom ingest` first``, test-first with the message tail pinned exactly, because the skills' Category-D error tables quote it verbatim and would otherwise re-import a raw module invocation.

## Plan Accuracy

The plan was exactly right — eight steps executed in order with no reordering and no deviations. Both anticipated challenges materialized and both mitigations worked: `make ci` stripped torch mid-run (twice) exactly as the m4 insight predicted, and sequencing live example execution before the CI gate made it a non-event; the over-trimming risk was neutralized by treating Category D as a literal keep-list during the edit and again during QA. The preflight radical-innovation step earned its keep here: converting the grep check into a test cost one small file and permanently pins the invariant the whole milestone exists to establish.

## Build & QA Observations

Build was transcription-smooth — the litter audit (written two days before the milestone ran) was effectively the creative phase, so the prose edits were mechanical application of a pre-existing inventory. The hygiene test's red→green arc over prose files worked exactly like a code TDD cycle: written red against the untrimmed skills, driven green by the edits. QA found nothing; the only borderline call it inspected was one sentence in the shared doc ("the fix is re-provisioning") which describes error routing rather than restating an operational rule.

## Insights

### Technical

- TDD works on prose deliverables when the assertion is mechanical: a content-invariant test (forbidden-token scan) written red before editing gives markdown the same red→green discipline as code, and survives as a regression pin. This generalizes the m6 lesson ("a grep-verifiable constraint is worth designing for") into "make the grep a test."
- Error messages are rendered-out surfaces: the engine's stderr hint carried a raw module invocation that every downstream error table would have re-quoted. When a contract changes shape, grep the *error strings*, not just the docs.

### Process

- A categorized audit with an explicit keep-list (Category D) converts a judgment-heavy editing pass into a mechanical one, and converts QA's "did we over-trim?" into a diff check. Writing the inventory *before* the milestone that applies it is what made this L2 instead of L3.

### Million-Dollar Question

If the on-path CLI had been a foundational assumption, the wrapper skills would have been *born* at this size — no invocation section beyond one line, no flag rationale, and the system-model doc written once in Phase 0 — and the litter audit, the m4 drift incident it catalogued, and this trimming pass would never have existed. What we built converges on that end-state exactly; the only cost of arriving late was the intermediate drift the shim was invented to end.
