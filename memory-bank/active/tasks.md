# Current Task: p5-distribution-release

**Complexity:** Level 4

## Preflight amendments

- **m1**: include a packaging/doc contract test pinning documented skill names / invocation forms to the skills tree (prevents install-doc drift; mirrors Phase-4 packaging assertion pattern).

## Advisory findings (non-blocking)

- **m3 / release-please trigger**: `.github/workflows/release-please.yaml` runs only on push to `main`; work is on `initialdev`. The m3 sub-run must merge (or otherwise land) on `main` before the release path can be exercised for real.
- **m1 / empirical verification**: confirming `/sr-*` vs `<plugin>:<skill>` requires live Cursor and Claude Code sessions — plan for operator participation, not a fully automated CI check.
- **m3 / clean-machine E2E**: marketplace add + plugin install are harness-UI steps; the sub-run should produce a checklist and evidence log, with operator driving the UI portions.
- **TDD**: L4 milestones defer detailed test-before-code ordering to each sub-run's plan phase (expected). m1's packaging contract is the only unit that must encode TDD in its L2 plan; m2/m3 are primarily config and operational proof.
