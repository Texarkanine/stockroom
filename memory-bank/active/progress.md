# Progress

Milestone m4 of L4 project `p3-onboarding-cli-scheduling`: build the `sr-initialize` onboarding skill's scheduling-and-first-run half — nightly ingest + embed installed via cron (Linux) or launchd (macOS) with entries invoking the shim (`stockroom ingest` / `stockroom embed`), idempotent re-install semantics, followed by a first full ingest + embed leaving a populated, embedded, query-ready warehouse. See `memory-bank/active/milestones.md` (m4) and `memory-bank/active/projectbrief.md`.

**Complexity:** Level 3

## 2026-07-08 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - `/niko` re-entry routed the L4 project through milestone advancement: m3 checked off, m3 sub-run ephemeral state deleted (`reflection/` and `projectbrief.md` preserved)
    - m4 classified as Level 3: complete feature across multiple components (two platform-specific scheduling mechanisms, idempotent installation semantics, per-machine resolution, first-run orchestration) that touches the system outside the repo, without system-wide architectural implications
    - Fresh sub-run ephemeral state written: `progress.md`, `activeContext.md`, stubbed `tasks.md`; `projectbrief.md` and `milestones.md` preserved
* Decisions made
    - Level 3 classification, matching the milestone's estimate — cron vs launchd mechanics, idempotency strategy, and how much lives in tested Python vs skill prose are design decisions reserved to this run
* Insights
    - Operator reports m3 was artisanally hand-verified on this machine's WSL *and* an M4 MacBook Pro — the macOS/MPS path the spike only reasoned about is now validated on a real target machine, satisfying the macOS half of project acceptance criterion 2
    - m3's plan already anticipated m4 reuse: `stockroom doctor probe`/`doctor smoke` should validate the environment before scheduler entries are installed
    - Cross-milestone invariant: scheduler entries invoke the shim (`stockroom ingest` / `stockroom embed`), never a raw engine path; Windows-native scheduling stays out of v1 (WSL is the Linux path)
