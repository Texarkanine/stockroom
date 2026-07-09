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

## 2026-07-09 - PREFLIGHT - COMPLETE (PASS)

* Work completed
    - TDD encoding, convention compliance, dependency impact, conflict detection, and completeness verified; `.preflight-status` written PASS
    - Traced every consumer of the old ``python -m stockroom.ingest`` hint: the two skill error tables (steps 4–5), `techContext.md` line 133 (step 7), archive docs (historical, untouched), and `ingest/__main__.py`'s own `prog=` (its real module name — not in scope)
    - Verified: plugin manifests point at `./skills/` as a directory (no file enumeration to update); `test_packaging.py`/`test_licensing.py` spot-check named paths only; REUSE globs cover both new files with no `REUSE.toml` change; the shim is live on this box (`stockroom 0.0.0` via PATH) and the warehouse is populated — B8 live-example dependencies satisfied
* Decisions made
    - One plan amendment (the radical-innovation step, applied in-scope): the m6 grep check is promoted from a one-shot manual command to a permanent pytest, `tests/test_skill_hygiene.py`, written red against the untrimmed skills before the prose edits and driven green by them — the no-invocation-token invariant becomes regression-pinned in CI forever, exactly like the m6 archive suggested ("a grep-verifiable constraint is worth designing for")
    - Steps renumbered 1–8 to fold the hygiene test in as step 2
* Insights
    - Module CLIs keep `prog="python -m stockroom.<mod>"` in their argparse usage lines; forwarded `--help` therefore still shows module-form usage. Cosmetic, out of m5 scope — noted as a future suggestion, not a finding

## 2026-07-09 - BUILD - COMPLETE

* Work completed
    - All 8 plan steps in order: engine hint swap (red→green, exact-pin tests), `test_skill_hygiene.py` written red against the untrimmed skills, `references/system-model.md` authored, `sr-query`/`sr-semantic` rewritten around `stockroom <subcommand>` (A–C out, D kept, one pointer each), `sr-search` breadcrumb extended, `systemPatterns.md`/`techContext.md` reconciled, full verification
    - `make ci` green end to end (365 passed, 3 torch-gated skips; REUSE 200/200); every shipped example live-executed through the real shim against the real warehouse before write-in; torch re-provisioned (cu126) and smoke green after the final gate
* Decisions made
    - Hygiene token list extended with `CLAUDE_PLUGIN_ROOT` (symmetry); error tables name both recoveries (`stockroom ingest` for a missing warehouse, `sr-initialize` for an unbound machine)
* Insights
    - The trimmed skills lost roughly a third of their prose with zero operational loss — the litter audit's Category D keep-list made the cut mechanical rather than judgment-heavy
    - `make ci` stripping torch mid-milestone happened again exactly as the m4 insight predicted; sequencing live examples before the CI gate (per the plan's mitigation) made it a non-event
