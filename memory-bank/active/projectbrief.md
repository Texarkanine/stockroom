# Project Brief

## User Story

As a power user of Stockroom, I want an Advanced usage docs section that covers escape-hatch workflows outside the agent harness, so I can operate the warehouse and CLI confidently when I have good reason to go beyond the normal User Guide path.

## Use-Case(s)

### Use-Case 1

A user who already completed `sr-initialize` wants to run `stockroom` subcommands from a terminal (not via `sr-*` skills) and needs clear, accurate guidance.

### Use-Case 2

A user wants to open the warehouse with the DuckDB CLI for ad-hoc SQL outside `stockroom query`, with the right safety caveats.

### Use-Case 3 (maybe)

A user wants to run the engine successfully via `uv` directly — only if we decide this is a real, documentable path worth including under the minimalism bar.

## Requirements

1. Deliver the **Advanced** docs section to the same reviewed quality bar as User Guide / Contributing / Architecture.
2. Cover confirmed topics: stockroom CLI out-of-band of an agent harness; DuckDB CLI against the warehouse.
3. Decide whether to include successful direct `uv` use of the engine (default lean: omit unless it clearly earns inclusion).
4. Keep the existing **shape**: landing page + sub-pages for specific advanced usages — content is not locked to the current scaffold prose.
5. Audience: smart users doing advanced things with good reason (user-guide voice, not Architecture atlas, not Contributing localdev).
6. Err on minimalism: if unsure users will take a path, or it is already covered in the User Guide, do not include it (e.g. catch-up ingest/embed, advanced dashboard, manual migrate unless they earn a place).

## Constraints

1. Docs-only — no product/code behavior changes unless a docs accuracy fix is unavoidable.
2. Not a second onboarding track — bootstrap/heal remain `sr-initialize` / User Guide.
3. Do not present `make` / `uv` from a git clone as an end-user substitute for initialize.
4. Do not blur ownership with User Guide, Architecture, or Contributing.
5. Prefer links over forking skill/`system-model` operational tables.

## Acceptance Criteria

1. Advanced section is coherent and presentation-quality under properdocs (`make docs-build` strict).
2. Confirmed topics are covered at appropriate depth; maybe-topics are either included with clear rationale or explicitly excluded.
3. Minimalism holds: no redundant UG recipes; no speculative advanced paths.
4. Landing + sub-page IA matches the agreed shape; nav and cross-links from related sections are clean.
5. Voice matches “power-user user-guide,” not systems atlas or contributor ritual.
