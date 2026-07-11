# Progress

Invert REUSE PPL-S from blanket `skills/**` to a narrow carve-out (`SKILL.md` + `references/**`), drop AGPL claw-back re-asserts, and verify with SPDX before/after.

**Complexity:** Level 2

## 2026-07-10 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - Intent confirmed: targeted PPL-S globs; drop rules 3 and 4; keep Chart.js MIT and `.cursor` NOASSERTION
    - Classified Level 2; initialized ephemeral memory-bank files
    - Saved SPDX baseline to `/tmp/stockroom-reuse-spdx/before.spdx`
* Decisions made
    - Prefer `skills/**/SKILL.md` + `skills/**/references/**` over blanket `skills/**/*.md`
* Insights
    - Claw-back lists exist only because of the broad PPL-S paint; narrowing removes the need for them
