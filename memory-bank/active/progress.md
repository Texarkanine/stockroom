# Progress

Add GitHub issue form(s) (bug + feature minimum; component split only if warranted) and a PR template. Design from stockroom's real triage/release needs; #100/#101 sketches are starting ideas, not specs. Blank issues stay enabled. Prose short; load-bearing fields stay.

**Complexity:** Level 2

## 2026-07-28 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - Clarified intent with operator (multiple issue templates, blank issues, sketches ≠ gospel, ADHD-short without omitting value)
    - Classified as Level 2
* Decisions made
    - Level 2: self-contained `.github/` enhancement; investigate component-split during planning, not assume it
* Insights
    - Org has PR templates (inquirerjs-checkbox-search, git-aliases) but no issue forms — stockroom is first

## 2026-07-28 - PLAN - COMPLETE

* Work completed
    - Mapped failure surfaces from troubleshooting docs vs doctor probe coverage
    - Wrote Level 2 implementation + TDD plan in tasks.md
* Decisions made
    - No per-component issue forms; Area dropdown on bug + feature forms
    - Bug form keeps doctor-first required field; feature form does not ask for doctor
    - Structural pytest under engine tests via repo_root (like test_packaging)
    - PR template stays short; conventional-commit title called out for release-please
* Insights
    - Field needs converge across components; routing ≠ separate YAML forms
