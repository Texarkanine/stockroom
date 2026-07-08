# Active Context

## Current Task: p3-onboarding-cli-scheduling
**Phase:** PLAN - COMPLETE

## What Was Done
- L4 milestone list generated (5 milestones) in `memory-bank/active/milestones.md`: m1 dispatcher (L2), m2 bake-then-verify shim (L3), m3 `sr-initialize` prereqs/torch/CLI (L3), m4 `sr-initialize` scheduling + first run (L3), m5 wrapper-skill trimming pass (L2)
- The roadmap's milestone 1 ("prerequisites, torch, and the on-path CLI") was split into m1/m2/m3 — bundled it would exceed L3 scope; the dispatcher and shim are independently deliverable and are the dependency root for everything else
- Cross-milestone invariants recorded (torch contract structural, no raw engine paths in rendered-out artifacts, dumb shim / tested dispatcher, no fallback incantations in skills, run-in-place packaging, TDD + artisanal skill verification, no Windows-native scheduling, chokepoints untouched)

## Next Step
- Preflight to validate the milestone list
