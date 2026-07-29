# Project Brief

## User Story

As a stockroom maintainer / user, I want `stockroom --version` (and the shim generator stamp) to stay in lockstep with the published release / plugin manifest version so that local diagnostics match GitHub releases and marketplace installs, and so I know whether a normal plugin update (session-start hook) refreshes what the shim reports.

## Use-Case(s)

### Use-Case 1

After a release bumps the plugin manifests to `N`, a fresh or updated install reports `stockroom N` from `stockroom --version`, not a stale older string.

### Use-Case 2

release-please’s next release PR automatically bumps `skills/sr-search/src/stockroom/__init__.py` alongside the manifests.

### Use-Case 3

Operator understands whether session-start `shim rectify` updates the version a shim reports after a plugin update (document the finding; change code only if the flow is broken for harness-owned shims).

## Requirements

1. Add a release-please generic marker (`x-release-please-version`) on the `__version__` line in `skills/sr-search/src/stockroom/__init__.py` so subsequent releases bump it.
2. Bump `__version__` to match the current release-please / plugin manifest version (`0.18.0`).
3. Extend packaging lockstep tests so `stockroom.__version__` cannot drift from the manifests / `.release-please-manifest.json` again.
4. Determine and record whether the normal update flow (session-start hook → `shim rectify`) updates the version a shim reports; fix only if harness-owned rectify is insufficient once `__version__` is correct.
5. Open a PR with the fix.

## Constraints

1. Do not invent a second version source of truth — keep release-please + manifests + `__version__` in lockstep.
2. Prefer the smallest change that restores sync and CI guardrails; no shim redesign unless investigation shows a real gap for harness owners.
3. Conventional commits; open PR after the fix is verified.

## Acceptance Criteria

1. `__version__` equals `.release-please-manifest.json` / both plugin manifest versions (`0.18.0` at time of fix).
2. `__init__.py` carries an `x-release-please-version` marker on the version line.
3. Packaging tests fail if `__version__` drifts from the RP/manifest sources.
4. Brief or reflection records a clear answer: does session-start rectify update what the shim reports (runtime `--version` vs baked `STOCKROOM_GENERATOR_VERSION`), including any owner/`dev` caveats.
5. A PR is open with the change.
