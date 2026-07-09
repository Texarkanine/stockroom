# Progress

Milestone m5 of L4 project `p3-onboarding-cli-scheduling`: the wrapper-skill trimming pass — create the shared system-model reference doc, swap every invocation incantation for `stockroom <subcommand>` across `sr-query` / `sr-semantic` / `sr-search`, apply the litter-audit inventory (Categories A–C out, D kept), add one shared-doc pointer per skill, and re-run the m6 grep-verifiable no-invocation-token check across all three. See `memory-bank/active/milestones.md` (m5) and `memory-bank/active/projectbrief.md`.

**Complexity:** Level 2

## 2026-07-09 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - `/niko` re-entry routed the L4 project through milestone advancement: m4 checked off, m4 sub-run ephemeral state deleted (`reflection/` and `projectbrief.md` preserved)
    - Post-milestone operator verification recorded in the m4 reflection: WSL cron entry fired overnight; M4 launchd works on-demand and passes validation (timer not yet observed firing, judged sufficient — artisanally-verified)
    - m5 classified as Level 2: a bounded editing pass over three existing skills plus one new reference doc within a single subsystem, with a pre-existing inventory (`planning/brainstorm/skill-litter-audit.md`) and a mechanical grep-verifiable check
    - Fresh sub-run ephemeral state written: `progress.md`, `activeContext.md`, stubbed `tasks.md`; `projectbrief.md` and `milestones.md` preserved
* Decisions made
    - Level 2 classification, matching the milestone's estimate — no open design decisions remain (the litter-audit inventory and the m6 no-invocation-token check both pre-exist)
* Insights
    - Both scheduling halves are now operator-verified live: the artisanal-verification deferral pattern (m3, m4) closed cleanly without blocking milestone advancement

## 2026-07-09 - PLAN - COMPLETE

* Work completed
    - Level 2 plan written to `tasks.md`: 8 behaviors (B1–B3 engine TDD: pin the new missing-warehouse hint exactly; B4–B8 prose: shared doc content, no-fallback contract, one pointer per skill, the m6 grep token check, live-executed examples), 7 ordered steps
    - Codebase survey: three wrapper skills read in full against the litter-audit inventory; engine grep found the stale ``run `python -m stockroom.ingest` first`` hint in `query.py`/`semantic.py`/`embed.py` (quoted verbatim by the skills' error tables); `systemPatterns.md` "Cross-skill resource resolution" section found still teaching the pre-shim contract
* Decisions made
    - Small in-scope engine amendment: the missing-warehouse hint becomes ``run `stockroom ingest` first`` (test-first — existing tests assert only `"ingest" in stderr`, to be tightened per the m4 pin-exactly lesson)
    - Shared doc lives at `skills/sr-search/references/system-model.md` — the engine home hosts the system model; sibling-relative pointers work in both installed and dev layouts; PPL-S coverage is automatic via the `skills/**` REUSE glob
    - Grep token set: `APP_DIR`, `PYTHONPATH`, `uv run`, `--no-sync`, `--no-config`, `CURSOR_PLUGIN_ROOT`, `find -L`, `python -m stockroom` — zero hits required across all three wrapper SKILL.md files
* Insights
    - The engine's own error text is a rendered-out surface too: a stderr hint naming a raw module invocation is the same drift class the milestone exists to remove, and the skills' Category-D error tables would otherwise re-import it verbatim
