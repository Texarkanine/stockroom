# Project Brief

## User Story

As a maintainer, I want every applicable SLOBAC smell from the 2026-07-11 audit verified and fixed so that the test suite asserts real product behavior instead of fossils, weak oracles, and presentation/prose pins.

## Use-Case(s)

### Use-Case 1

Walk each of the 60 findings in `.slobac/2026-07-11T14-58-48/audit.md`, confirm against live tests and the SLOBAC taxonomy, then remediate or explicitly dismiss as non-applicable.

### Use-Case 2

Prefer deleting dashboard-display / skill-content / docs-prose tests that are prose-pin, loose-text-oracle, or presentation-coupled rather than locking specific copy — keep coverage on actual code behavior.

## Requirements

1. Source of truth for findings: `.slobac/2026-07-11T14-58-48/audit.md` (60 findings).
2. Verify each finding against the live test and https://texarkanine.github.io/slobac/taxonomy/ before changing code.
3. Apply prescribed remediations for findings that hold; record and skip false positives / non-applicable items.
4. For smells near prose-pin / loose-text-oracle / presentation-coupled on dashboard display or skill/docs contents: err toward deletion rather than goldenizing output.
5. Prefer behavioral coverage of product code over editorial/presentation oracles.
6. Follow TDD where implementation/SUT changes are required; for pure test remediations, change tests and keep the suite green.

## Constraints

1. Scope is the audited suite (paths referenced in the audit under the stockroom test tree).
2. Do not invent net-new product features beyond what remediation needs (e.g. structured error fields only if required to replace loose text oracles on real code paths).
3. Preserve regression-detection power for kept tests (semantic-redundancy deletes must be strict subsets / folded as prescribed).

## Acceptance Criteria

1. Every audit finding is either remediated or documented as verified non-applicable / false positive with rationale.
2. Remaining tests exercise product code behavior; deleted presentation/prose/skill pins are gone.
3. Full relevant test suite passes after remediations.
4. Deliverable-fossils checklist prefixes (B#/T#/F#/Phase-N) are stripped from kept tests; naming-lies and vacuous/conditional smells on code paths are fixed per taxonomy.
