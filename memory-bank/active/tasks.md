# Current Task: p3-onboarding-cli-scheduling

**Complexity:** Level 4

*The L4 milestone decomposition lives in `memory-bank/active/milestones.md` (5 milestones: m1 dispatcher, m2 shim, m3 sr-initialize prereqs/torch/CLI, m4 scheduling + first run, m5 trimming pass). Each milestone runs as its own L1/L2/L3 sub-run; this file is repopulated per sub-run by that run's plan phase.*

## Preflight Findings (2026-07-08, PASS)

- **Amended into the plan**: `stockroom.migrate` is library-only (no `main()`/argparse) — m1 authors its CLI entrypoint before the dispatcher can forward to it. README documentation updates assigned: dispatcher usage → m1, ad-hoc-invocation section rewritten around `stockroom <subcommand>` → m2.
- **Advisory (for m3's sub-run)**: consider shipping the torch smoke test as a tested `stockroom doctor` dispatcher subcommand (torch version, `cuda.is_available()`, encode-one-string, warehouse reachability, shim-staleness report) rather than skill prose — permanent diagnostic surface, reusable long after setup.
- **Advisory (for m4's sub-run)**: launchd (macOS) cannot be live-validated on this WSL2 machine — plan for unit-tested plist generation with live validation deferred to a macOS machine; the roadmap's "CPU-or-macOS path" acceptance criterion is satisfiable via a CPU-forced torch path on Linux.
- **Verified**: no manifest changes needed for the new `sr-initialize` skill dir (Cursor manifest points at `./skills/`; Claude discovers `skills/` by convention); `python -m stockroom` does not collide with the existing `python -m stockroom.ingest` sub-package entrypoint; module CLIs remain unchanged public surfaces (dispatcher wraps, never reimplements).
