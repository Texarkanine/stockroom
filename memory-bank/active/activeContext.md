# Active Context

## Current Task: warehouse-file-growth (L4 re-plan, 2026-10-22)
**Phase:** PREFLIGHT - COMPLETE (PASS WITH ADVISORY)

## What Was Done
- Milestones 1 and 2 done. The personal Mac shadow gate passed on Puck against `ce16489`
- Milestone 3's first plan (zstd edited into `0001`, runner drops the clause on old files) passed preflight, then was withdrawn after the operator's rulings below
- L4 re-plan: brief amended, `milestones.md` invariants and milestones 1, 3, 5, and 6 updated (7 milestones, 2 done). Milestone 3 now restores released migrations and adds the frozen schema file and new-warehouse path
- Branch `constrain-size-as-best-we-can` is pushed (`ce16489` and Tachi's `ae39a67`). No pull request yet

## Operator rulings (2026-10-22)
- Released migrations are never edited, comments included. Restore every one milestone 1 changed (`0003`, `0001`'s comments, the `0003` to `0008` snapshots, and their tests)
- One chain forever, plus a frozen schema file pinned to one chain version (9) for new warehouses. They record one `schema_version` row naming it and migrate forward to the head. They never run `0003`, so the engine never loads `vss`. No second v2 chain, no declarative tool
- No runner rule that records a version without running it
- A warehouse that cannot reach the head stops in an error state that users must resolve. Code after the DuckDB 2.0 point never copes with older states
- Old-format warehouses may not persist. The copy-and-swap is the durable v1-to-v2 step of the chain, not a short-lived utility
- Schema provenance may change in a way that cannot migrate only at a major version break, and a copy-into-a-new-database tool is not an option for stockroom
- Milestones 1 to 3 make the first release on this branch. The pull request opens only after milestone 3 restores the released migrations, and the Mac gate re-runs after milestone 3
- "Why?" from the operator is a real question, not pushback

## Operator review of the L4 preflight (2026-10-22)
- Comments in migrations may be added or changed. Changing SQL to do something materially different is not allowed. Milestone 1's comment edits to `0001` stay; `0003`'s SQL and name are restored. Later ERD edges can go into migrations as comments
- Filesystems that refuse hard links: APFS, Mac OS Extended (Journaled), ext4, and NTFS all support them, so they are out of scope. There is no skip, test, or lasting-skip handling for them, and milestone 6's lasting-skip error state is dropped (a skip retries)
- Validate the new-warehouse path on real data in milestone 3, and a new install must still work at the end (brief acceptance 12, milestone 7)
- Folded in on the agent's judgment, with no objection:
    - requirement wording "the latest release's SQL"
    - an immutability gate in `make ci` and CI that compares SQL with comments and whitespace removed
    - the format-boundary constant as the check's precondition
    - milestone 2's schema-1 test becomes the stop test
    - the stale `systemPatterns` sentence is deleted
    - the commit order is relaxed
    - temp-then-rename creation in milestone 3, extended by milestone 5
    - split milestone 6 only if it classifies above Level 3

## Next Step
- Operator: `/niko` to classify milestone 3 (the review is done and folded in)
