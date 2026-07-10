# Project Brief

## User Story

As a stockroom maintainer, I want the memory bank, README, and user-facing docs to reflect stockroom as it exists today (v1 complete), and the obsolete `planning/` tree removed, so that contributors and agents ground on present-tense reality rather than build-sequence history.

## Use-Case(s)

### End-of-roadmap cutover

The v1 roadmap (Phases 0–5) is finished. Persistent memory-bank files must stand alone with zero references into `planning/`. User-facing install/usage material that outgrew a slobac-level README moves into `docs/`. The README shrinks to present-tense product orientation. Then `planning/` is deleted.

## Requirements

1. Re-initialize `memory-bank/productContext.md`, `systemPatterns.md`, and `techContext.md` from the current codebase and product state (not as thin pointers into planning briefs).
2. Persistent memory-bank prose must not use hard line-breaks.
3. Create a `docs/` directory and move content that truly belongs in user-facing documentation into markdown file(s) there.
4. Trim the root README to roughly the slobac level: short, present-tense, describing how stockroom is — not how it came to be or what might be planned.
5. Delete the entire `planning/` directory once the above has absorbed what still matters.
6. After cutover, `memory-bank/` (and other kept docs) must contain zero references to `planning/`.

## Constraints

1. Do not invent product behavior; document what exists.
2. Do not keep origin-story, roadmap, spike, or future-commitment material in README, `docs/`, or persistent memory-bank files.
3. Agent-facing working instructions already in `.cursor/rules/` must not be duplicated into persistent memory-bank files.
4. Prefer clean-break: planning artifacts (briefs, brainstorm, spikes) are discarded, not archived into `docs/`.

## Acceptance Criteria

1. All three persistent memory-bank files are self-contained, present-tense, and free of hard-wrapped prose and `planning/` references.
2. `docs/` exists with user-facing documentation relocated from the oversized README / planning material as appropriate.
3. README is slobac-comparable in length and tone, present-tense only.
4. `planning/` is gone from the tree.
5. No remaining references to `planning/` in kept project docs (memory-bank persistent files, README, `docs/`).
