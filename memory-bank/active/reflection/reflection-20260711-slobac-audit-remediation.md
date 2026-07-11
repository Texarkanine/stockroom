---
task_id: 20260711-slobac-audit-remediation
date: 2026-07-11
complexity_level: 3
---

# Reflection: SLOBAC audit remediation

## Summary

Verified and remediated all 60 SLOBAC audit findings (plus supplemental schedule/schema fossils) in the `skills/sr-search` test suite. Preferring deletion of presentation/prose pins and strengthening behavioral oracles; full suite green with no production API changes.

## Requirements vs Outcome

Delivered as specified: every audit finding remediated or would have been documented N/A (none were N/A); supplemental `test_schedule.py` / `test_schema_0002.py` fossils stripped; presentation/skill pins deleted rather than goldenized; suite green. No requirements dropped or added beyond the operator’s preflight-scope amendment (already folded into the plan before build).

## Plan Accuracy

Batch ordering (delete → fossils → conditional/naming → public-surface → redundancy → torch oracles → verify) matched reality and kept risk low. File lists were accurate. The main surprise was self-inflicted: an over-aggressive fossil-strip script briefly corrupted Black formatting via cross-line/`space-collapse` edits — restored and redone with docstring/phrase-local transforms. Preflight’s session-pane surgical strip and `_iso` delete amendments were correct and avoided wasted work.

## Creative Phase Review

No creative phase — dispositions were taxonomy-prescribed and operator-settled. That was the right call; nothing during build required a design fork.

## Build & QA Observations

Build was mostly mechanical once Batch 0 confirmed all findings still held. Torch exact-reason asserts needed no SUT constant extraction. QA was clean (no substantive findings); a naive `_mtime(` grep false-positived on `by_mtime()` and was dismissed.

## Cross-Phase Analysis

Operator delete preference + preflight amendments prevented the highest-risk failure mode (goldenizing UI/skill copy). Bounded supplemental fossils prevented an open-ended suite fossil hunt during build. Skipping creative avoided overhead without cost because smell dispositions were already prescribed.

## Insights

### Technical
- Fossil renames must be docstring/phrase-local; never “normalize whitespace” across a whole test file when stripping checklist ids — Black hanging indents and multi-line calls are fragile under global space collapse.
- Exact soft-fail `reason` strings from `torch_source` are stable enough to assert verbatim when the template is built from `requirements_path()` / timeout values the test already controls.

### Process
- For smell remediations, verify-then-delete-first ordering pays off: presentation pins gone early reduces noise while rewriting behavioral tests.
- Preflight amendments that narrow “delete vs strengthen” for mixed presentation/JS-coupled tests (session pane) are high leverage — build would otherwise thrash on that judgment call.
