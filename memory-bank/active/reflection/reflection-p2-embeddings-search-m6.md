---
task_id: p2-embeddings-search-m6
date: 2026-07-07
complexity_level: 3
---

# Reflection: `sr-search` skill (p2-embeddings-search m6)

## Summary

Rewrote `skills/sr-search/SKILL.md` from its Phase-0 skeleton into the model-invocable judgement skill that routes a question to `sr-query` / `sr-semantic` (or both) and synthesizes one answer. Built to plan, QA clean, all gates green — the final milestone of the Phase-2 L4 project.

## Requirements vs Outcome

Every milestone requirement and the operator's litter constraint were delivered: routing judgement with the four verified cases as shipped examples, delegation by sibling name with one relative-path fallback and no invocation section, the four synthesis rules plus truncation-by-delegation and relaying posture, and a one-line engine-home breadcrumb. One addition beyond the plan's letter: an empty-result fallback line ("try the other surface before concluding the content isn't there") — accepted in QA as guardrail-as-action. Nothing dropped or reinterpreted.

## Plan Accuracy

The six-step plan executed in order with no reordering, splitting, or additions. The anticipated challenges resolved exactly as predicted: `make ci`'s sync stripped torch and `make torch` restored it (m4/m5 precedent); the m4/m5 template was used for structure only, and the litter grep came up clean on the first pass. The no-edits predictions (siblings, manifests, `REUSE.toml`, README) all held, as did preflight's finding that `test_skeleton_skill_front_matter` stays green through the front-matter flip.

## Creative Phase Review

- **Delegation mode (Option A — name + relative-path fallback)**: held up completely. The consequence predicted in the creative — no invocation section at all — made the finished orchestrator the leanest of the three wrapper skills (36 lines) and mooted the litter audit's "m6 inherits the invocation litter" concession.
- **Synthesis grain (Option C — narrated default, judgement-ordered list on request)**: translated directly into six actionable lines with zero friction; the id-based dedup rule was exercised live in the both-surfaces pass (semantic `--format json` put the ids in hand exactly as the siblings document).
- **Search-surface architecture (Option 3, project-level)**: this milestone was its final proof — judgement shipped as prose, operations stayed in the siblings, and no fusion code was ever needed.

## Build & QA Observations

Build was a single-file rewrite with no iteration: the two creatives plus the preflight amendment (desk-check cases shipped as routing examples) meant the content was effectively fully specified before authoring began. Live verification ran three end-to-end passes against the real warehouse (exact, meaning, both-surfaces) by following the skill as written — no improvisation was needed, which was the test. QA found nothing; its one judgement call worth keeping: routing discriminators are the router's *own* task knowledge, not Category B duplication of the siblings' "when to use" sections.

## Cross-Phase Analysis

The causal chain ran forward cleanly: the architecture creative (project-level) eliminated the fusion module → the delegation-mode creative eliminated the invocation section → the litter pass had almost nothing to catch at build time. The preflight amendment unifying verification cases with shipped content removed a whole class of drift (examples that diverge from what was tested). This is the second sub-run in a row (after m5) where autonomous creatives resolved all open questions before plan, and build proceeded with zero rework — for prose deliverables, front-loading design into creatives appears to convert build into transcription.

## Insights

### Technical

- Delegation-by-name between sibling skills needs no plumbing because committed layout = install layout guarantees the relative path in every install; this generalizes to any future cross-skill reference in this plugin.
- The grep-verifiable no-invocation-token check (`APP_DIR|PYTHONPATH|uv run|no-sync|no-config|python -m`) makes the "no operational duplication" constraint auditable in one command — reuse it in the Phase-4 trimming pass across all three wrapper skills.

### Process

- Shipping verification cases as the artifact's own examples (the preflight amendment) is the m4/m5 "every shipped example is verified" discipline generalized: wherever content and test cases can be the same artifact, make them so.
- The litter test's boundary clarified for orchestrator skills: criteria the skill needs to *make its own decision* (routing discriminators) are task knowledge even when they echo a sibling's topic; content the *delegated-to* skill needs is duplication. This distinction will matter again when `sr-initialize` (Phase 4) is authored.
