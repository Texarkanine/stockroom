# Task: semantic-cli-filters

* Task ID: semantic-cli-filters
* Complexity: Level 2
* Type: rework

Stop listing `--harness` and `--role` on the human pages that already refuse to duplicate skill flags. Leave the flags in `skills/sr-semantic/SKILL.md`. Do not change the engine, the tests, or the two-path rank.


## Test Plan (TDD)

### Behaviors to Verify

No new executable behavior.

### Test Infrastructure

- Framework: none for this rework
- Test location: none
- Conventions: prose and policy edits do not get change-detector tests
- New test files: none

## Implementation Plan

### 1. CLI page — prose/policy [x]

- Files: `docs/advanced/cli.md`
- No tests: prose/policy artifact

1. Remove the second example, `stockroom semantic --harness claude --role user "flaky dashboard tests"`. Leave the unscoped `-k 10` example.
2. Restore the Role cell to `Vector (semantic) search.` The column is the subcommand's job. Do not mention `--role` or `--harness` there.
3. Do not add those flags to the Output shape list. That list is the shared presentation flags, `--format` and `--detail`.

### 2. Search page — prose/policy [x]

- Files: `docs/user-guide/search.md`
- No tests: prose/policy artifact

1. Remove the sentence that lists `--harness` and `--role` from the `sr-semantic` section. The page already says operational flags live in each skill's `SKILL.md` and that this page does not duplicate them.
2. Leave the unscoped `stockroom semantic "how does the warehouse locking work"` example.

### 3. Skill index — prose/policy [x]

- Files: `docs/user-guide/skills.md`
- No tests: prose/policy artifact

1. Remove `optionally scoped to one harness or to user / assistant` from the `sr-semantic` blurb.
2. Keep the sharpened boundary: not for id lookups, counts, dates, or projects. That sentence does not name the flags. Reverting it to "id filters or counts" would hide the boundary this feature drew.

### 4. Leave the flag home where it is — prose/policy [x]

- Files: `skills/sr-semantic/SKILL.md`, `skills/sr-search/SKILL.md`
- No tests: prose/policy artifact

1. Do not add another flag section. `sr-semantic` already has the pronoun map, the accepted values, and the empty-result meaning.
2. Leave the `sr-search` route row. That skill decides when to pass the flags. It is not a human flag table.
3. Leave `docs/architecture/embeddings.md` and `memory-bank/systemPatterns.md`. Those sentences describe the two rank paths, not how to type the command.

## Technology Validation

No new technology - validation not required

## Dependencies

- The flags and the pronoun map already in `skills/sr-semantic/SKILL.md`
- Review 5420273503 on pull request 136

## Challenges & Mitigations

- The skill-index edit also sharpened "not for id filters or counts" into "not for id lookups, counts, dates, or projects." That boundary is not a flag listing. Delete only the scope clause.
- The CLI bash block is an example, and the review hunk included it. Remove that example anyway. The page says it does not fork skill flag tables, and one unscoped example is the pattern the rest of the block already uses.

## Pre-Mortem

- The rework also edits the engine or the tests, and the review was only about where the flags are written. Steps 1–3 name the three human sentences. Step 4 names what stays.
- `sr-search` loses its route row because it mentions the flags. That row is how the router passes a scope. Step 4 keeps it.

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Pre-Mortem complete
- [x] Preflight
- [x] Build
- [x] QA (PASS)

## QA Results

PASS. The rework diff touches only the three planned doc files and matches steps 1-4. The flag home (`skills/sr-semantic/SKILL.md`), the `sr-search` route row, and the architecture two-path sentence are intact. No KISS, DRY, YAGNI, completeness, regression, integrity, or documentation findings. Advisory: the untracked `.cursor/skills/stockroom-local/` is unrelated and should stay out of this commit.
