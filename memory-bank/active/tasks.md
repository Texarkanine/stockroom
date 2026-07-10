# Task: p5-m1-install-docs

* Task ID: p5-m1-install-docs
* Complexity: Level 2
* Type: Simple enhancement

Author user-facing install and usage documentation covering marketplace-add and local/dev load paths; document per-harness skill invocation forms from platform contracts; confirm dual-manifest layout. Live marketplace install + empirical invocation proof deferred until stockroom is listed in `txrk9-agent-plugins` and exercised from `main` (m2/m3).

**Operator decisions (build):**
- No packaging/doc contract tests — docs free to rewrite without CI pins.
- Cannot validate standalone plugin install without a marketplace entry (Cursor folder picker and Claude permanent install are marketplace-shaped); write best-effort docs now; fix later after index lands.

## Test Plan (TDD)

### Behaviors to Verify

- [Regression]: existing packaging contracts (`test_packaging.py` manifests/hooks/release-please) and `test_skill_hygiene.py` still pass
- No new tests for README / planning-doc prose

## Implementation Plan

1. [x] ~~Failing packaging/doc contract~~ — **dropped** per operator
2. [x] **Install & usage documentation** — README rewritten: marketplace path (Cursor + Claude, via txrk9-agent-plugins), local/dev loaders (`~/.cursor/plugins/local/` + `claude --plugin-dir`), first-time setup, skill table, usage; honest about not-yet-listed and unverified invocation forms
3. [x] **Empirical invocation verification** — **deferred** to post-marketplace / `main` (m2/m3). Docs cite platform contracts; README states forms are not yet proven against a marketplace install of stockroom
4. [x] **Manual-install smoke** — dual-manifest layout confirmed on disk; Cursor "add from folder" correctly rejected (marketplace UI); documented real local/dev paths instead
5. [x] **Green suite** — `make test` 424 passed / 3 skipped / 32 JS; packaging 10/10

## Technology Validation

No new technology - validation not required

## Dependencies

- Dual manifests + `skills/` tree (Phase 0)
- Marketplace listing (m2) + release on `main` (m3) for live install/invocation proof
- Official docs: [Cursor Plugins](https://cursor.com/docs/plugins), [Claude Code plugins](https://code.claude.com/docs/en/plugins), [txrk9-agent-plugins README](https://github.com/Texarkanine/txrk9-agent-plugins)

## Challenges & Mitigations

- **No marketplace yet**: document intended path + local/dev loaders; defer E2E proof
- **Docs may drift**: accepted — no CI pins; fix when m2/m3 exercise the real path

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD) — amended: no doc pins
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Preflight
- [x] Build
- [x] QA
