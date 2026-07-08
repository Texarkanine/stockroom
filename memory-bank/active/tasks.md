# Current Task: p3-m1-stockroom-dispatcher

**Complexity:** Level 2

*Sub-run of L4 project `p3-onboarding-cli-scheduling` — milestone m1. Task list to be populated by the L2 plan phase.*

## Carried-in Preflight Findings (L4 preflight, 2026-07-08, PASS)

- `stockroom.migrate` is library-only (no `main()`/argparse) — m1 authors its CLI entrypoint before the dispatcher can forward to it.
- README documentation update assigned to m1: dispatcher usage.
- Verified: `python -m stockroom` does not collide with the existing `python -m stockroom.ingest` sub-package entrypoint; module CLIs remain unchanged public surfaces (dispatcher wraps, never reimplements).
