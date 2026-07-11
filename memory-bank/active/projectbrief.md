# Project Brief

## User Story

As a maintainer, I want every applicable SLOBAC smell from the 2026-07-11 audit verified and fixed so that the test suite asserts real product behavior instead of fossils, weak oracles, and presentation/prose pins.

## Use-Case(s)

### Use-Case 1

Walk each of the 60 findings in `.slobac/2026-07-11T14-58-48/audit.md`, confirm against live tests and the SLOBAC taxonomy, then remediate or explicitly dismiss as non-applicable. Also strip obvious deliverable-fossils in the same suite that the audit missed (`test_schedule.py` checklist ids; `test_schema_0002.py` Phase-1 module fossil).

### Use-Case 2

Prefer deleting dashboard-display / skill-content / docs-prose tests that are prose-pin, loose-text-oracle, or presentation-coupled rather than locking specific copy — keep coverage on actual code behavior.

## Requirements

1. Primary source of findings: `.slobac/2026-07-11T14-58-48/audit.md` (60 findings).
2. Supplemental in-scope fossils (same smell, missed by audit): all `B#`/`B17` deliverable-fossil docstrings in `skills/sr-search/tests/test_schedule.py` (including the module header), and the Phase-1 “Done When” fossil in `skills/sr-search/tests/test_schema_0002.py`.
3. Verify each finding against the live test and https://texarkanine.github.io/slobac/taxonomy/ before changing code.
4. Apply prescribed remediations for findings that hold; record and skip false positives / non-applicable items.
5. For smells near prose-pin / loose-text-oracle / presentation-coupled on dashboard display or skill/docs contents: err toward deletion rather than goldenizing output.
6. Prefer behavioral coverage of product code over editorial/presentation oracles.
7. Follow TDD where implementation/SUT changes are required; for pure test remediations, change tests and keep the suite green.

## Constraints

1. Scope is the audited suite under `skills/sr-search/tests` (+ `tests-js`), plus the supplemental fossil files named above.
2. Do not invent net-new product features beyond what remediation needs (e.g. structured error fields only if required to replace loose text oracles on real code paths).
3. Preserve regression-detection power for kept tests (semantic-redundancy deletes must be strict subsets / folded as prescribed).

## Acceptance Criteria

1. Every audit finding is either remediated or documented as verified non-applicable / false positive with rationale.
2. Supplemental schedule + schema_0002 deliverable-fossils are stripped (behavior claims kept).
3. Remaining tests exercise product code behavior; deleted presentation/prose/skill pins are gone.
4. Full relevant test suite passes after remediations.
5. Deliverable-fossils checklist prefixes (B#/T#/F#/Phase-N) are stripped from kept in-scope tests; naming-lies and vacuous/conditional smells on code paths are fixed per taxonomy.
