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

## 2026-07-08 - CREATIVE - COMPLETE

* Work completed
    - One open question explored and resolved with high confidence: `creative-scheduling-surface.md` (architecture) — where scheduling logic lives and how idempotent entry management works
    - Led with the never-do list per the established process insight: never a raw engine path in an entry, never touch a foreign crontab line, never accumulate duplicate entries, never assume the scheduler's PATH, never install silently against a dead cron daemon
* Decisions made
    - Q1: new flat `stockroom.schedule` module (the dispatcher's eighth subcommand: `install | status | remove`) with injectable `crontab`/`launchctl` runners; cron idempotency via a marker-delimited managed block (the Makefile localdev precedent), launchd idempotency via an owned `com.stockroom.nightly.plist`; one shared payload renderer (`date; stockroom ingest && stockroom embed` → nightly log) for both platforms; entries invoke the shim by name, resolvable under cron's minimal environment through an install-time-resolved absolute `PATH=` prefix (`shutil.which` on uv and the shim)
    - Prose-only rejected (untestable foreign-crontab filtering — an unrecoverable failure mode); extending `stockroom.shim` rejected (different lifecycle/ownership policies would interleave)
    - Judgment stays in `sr-initialize` prose: consent to install, time-of-night (default 03:30), the daemon-not-running warning relay, and first-run orchestration (`stockroom ingest --full` + `stockroom embed` over the shim — no new engine code)
* Insights
    - The scheduler's execution environment is the real adversary: cron's `PATH=/usr/bin:/bin` resolves neither uv nor the shim, `%` is cron syntax, and a POSIX `PATH=` prefix cannot precede an `&&` list directly — hence the `/bin/sh -c '…'` wrapper in the rendered entry
    - `schedule status` is what extends "the environment is the state" re-entry contract to scheduling — the skill re-probes instead of tracking progress
    - Third application of the judgment-vs-mechanism split (search m6, onboarding m3, scheduling m4) — it is now safely a load-bearing project pattern
