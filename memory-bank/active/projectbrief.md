# Project Brief

## User Story

As a stockroom maintainer, I want PPL-S applied only to prompt-shaped skill payload (`SKILL.md` and `references/**`) so that everything else under `skills/**` stays AGPL by default, without claw-back re-assert lists.

## Use-Case(s)

### License resolution for skill prompts

`skills/*/SKILL.md` and `skills/**/references/**` resolve to PPL-S.

### License resolution for engine/software

Python, shell, SQL, lockfiles, tests, dashboard assets inherit base AGPL; Chart.js stays MIT; `.cursor/**` stays NOASSERTION.

### SPDX before/after audit

Capture `reuse spdx` before and after the change and confirm only the intended license flips occurred.

## Requirements

1. Narrow PPL-S in `REUSE.toml` to `skills/**/SKILL.md` and `skills/**/references/**`.
2. Remove AGPL re-assert blocks for code-shaped paths and dashboard assets (rules 3 and 4).
3. Keep Chart.js MIT and `.cursor/**` NOASSERTION overrides.
4. Update `REUSE.toml` comments, `test_licensing.py`, and `systemPatterns.md` layered-licensing prose to match.
5. Save SPDX manifests before and after; report any file whose resolved license changed.

## Constraints

1. Do not broaden PPL-S to all `skills/**/*.md` (test fixture READMEs stay AGPL).
2. Worst-case AGPL remains the intentional default.

## Acceptance Criteria

1. `reuse lint` is clean.
2. Licensing tests pass with the inverted model (prompt paths PPL-S; code paths AGPL without needing claw-back).
3. SPDX before/after diff shows only expected flips (no accidental license changes on software/assets).
4. Persistent system-patterns licensing blurb matches the new model.
