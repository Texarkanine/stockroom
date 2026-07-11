---
task_id: reuse-ppls-narrow-carveout
complexity_level: 2
date: 2026-07-10
status: completed
---

# TASK ARCHIVE: reuse-ppls-narrow-carveout

## SUMMARY

Inverted REUSE so PPL-S is a narrow carve-out (`SKILL.md` + `references/**`) instead of a blanket `skills/**` paint with AGPL claw-back re-asserts. SPDX before/after showed zero per-file license flips on the current tree; `make ci` stayed green (512 passed, 3 skipped; 52 JS; reuse compliant).

## REQUIREMENTS

1. Narrow PPL-S in `REUSE.toml` to `skills/**/SKILL.md` and `skills/**/references/**`.
2. Remove AGPL re-assert blocks for code-shaped paths and dashboard assets (former rules 3 and 4).
3. Keep Chart.js MIT and `.cursor/**` NOASSERTION overrides.
4. Update `REUSE.toml` comments, `test_licensing.py`, and `systemPatterns.md` layered-licensing prose to match.
5. Save SPDX manifests before and after; report any file whose resolved license changed.
6. Do not broaden PPL-S to all `skills/**/*.md` (fixture READMEs stay AGPL).

## IMPLEMENTATION

### Approach

Replaced the broad `skills/**` PPL-S annotation with targeted globs for prompt-shaped payload only. Dropped the AGPL claw-back lists that existed solely to undo that broad paint. Software under `skills/**` now inherits base AGPL by default.

### Key files

| Area | Files |
| --- | --- |
| REUSE invert | `REUSE.toml` |
| Licensing tests | `skills/sr-search/tests/test_licensing.py` |
| Patterns | `memory-bank/systemPatterns.md` (layered licensing blurb) |

## TESTING

- TDD: updated `test_licensing.py` for inverted model — PPL-S on `SKILL.md` + `references/system-model.md`; AGPL on code/shell/dashboard/fixture README; Chart.js MIT; `reuse lint` clean.
- SPDX before/after: zero `LicenseInfoInFile` flips on the tracked tree (expression-only invert for today's layout).
- Full suite: **512 passed, 3 skipped**; 52 JS; `make ci` / `reuse lint` green.
- `/niko-qa` semantic review PASS; no fixes required.

## LESSONS LEARNED

### Technical

For this repo's current `skills/` layout, broad-then-claw-back and narrow-carve-out resolve to identical SPDX license sets — the value of the invert is failure-mode direction (new software stays AGPL by default), not a license outcome change today.

### Process

Nothing notable. Plan sequence matched the build; QA found nothing to fix.

### Million-dollar question

Starting from "AGPL base + PPL-S only on prompt payload paths" is what we shipped. The claw-back list was an artifact of painting the whole skill directory first; with the engine living under `skills/sr-search/`, the narrow carve-out is the natural expression.

## PROCESS IMPROVEMENTS

None — plan, preflight, build, QA, and reflect held without rework.

## TECHNICAL IMPROVEMENTS

None beyond the shipped invert. Prefer narrow carve-outs over broad paint + claw-back when the engine and prompt payload share a tree.

## NEXT STEPS

None. Task complete and archived.
