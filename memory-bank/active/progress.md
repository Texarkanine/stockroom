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
    - Q1: new flat `stockroom.schedule` module (the dispatcher's eighth subcommand: `install | status | remove`) with injectable `crontab`/`launchctl` runners; cron idempotency via a marker-delimited managed block (the Makefile localdev precedent), launchd idempotency via an owned `jp.ne.cani.stockroom.nightly.plist`; one shared payload renderer (`date; stockroom ingest && stockroom embed` → nightly log) for both platforms; entries invoke the shim by name, resolvable under cron's minimal environment through an install-time-resolved absolute `PATH=` prefix (`shutil.which` on uv and the shim)
    - Prose-only rejected (untestable foreign-crontab filtering — an unrecoverable failure mode); extending `stockroom.shim` rejected (different lifecycle/ownership policies would interleave)
    - Judgment stays in `sr-initialize` prose: consent to install, time-of-night (default 03:30), the daemon-not-running warning relay, and first-run orchestration (`stockroom ingest --full` + `stockroom embed` over the shim — no new engine code)
* Insights
    - The scheduler's execution environment is the real adversary: cron's `PATH=/usr/bin:/bin` resolves neither uv nor the shim, `%` is cron syntax, and a POSIX `PATH=` prefix cannot precede an `&&` list directly — hence the `/bin/sh -c '…'` wrapper in the rendered entry
    - `schedule status` is what extends "the environment is the state" re-entry contract to scheduling — the skill re-probes instead of tracking progress
    - Third application of the judgment-vs-mechanism split (search m6, onboarding m3, scheduling m4) — it is now safely a load-bearing project pattern

## 2026-07-08 - PLAN - COMPLETE

* Work completed
    - Component analysis: `stockroom.schedule` (new flat module), dispatcher eighth `SUBCOMMANDS` row, `sr-initialize` SKILL.md steps 8–9 (scheduling consent/install + first full ingest/embed), README/techContext/systemPatterns accretion; `warehouse.home_dir()` reused for the nightly log; no schema or existing-signature changes
    - Test plan: 17 behaviors — payload rendering + `%`-guard + `--time` validation (B1–B2), cron foreign-line preservation / idempotent re-install / shim-missing refusal / daemon warning / remove / status (B3–B9, B17), launchd plist shape + idempotency + shared guard (B10–B13), platform dispatch + CLI + dispatcher fingerprint (B14–B16); new `test_schedule.py` / `test_schedule_cli.py`, extended `test_dispatcher_cli.py`
    - Six-step ordered plan written to `tasks.md`: payload → cron → launchd → dispatch/CLI (each red→green) → SKILL.md prose (every example executed live first) → docs + live validation + `make ci`
* Decisions made
    - Live validation protocol for the operator's real crontab: back up first, diff foreign lines byte-for-byte after every mutate step; unit tests (B4/B5/B8) lock the filter before it touches the real thing
    - launchd closed the m3 way: injected-seam unit tests here, artisanal validation on the operator's M4
    - First run is orchestration-only prose (`stockroom ingest --full` → `stockroom embed` → count sanity-check through the shim) — no new engine code, it validates wiring over the m1/m2-tested surfaces
* Insights
    - The milestone's real risk concentrates in the cron execution environment, not the Python: every mitigation (absolute `PATH=` prefix, `/bin/sh -c` wrapper, `%`-free payload) is structural and test-pinned rather than documented-only

## 2026-07-08 - PREFLIGHT - COMPLETE (PASS)

* Work completed
    - TDD encoding, convention compliance, dependency impact, conflict detection, and completeness verified against the codebase; `.preflight-status` written PASS
    - Verified: `schedule` name is unclaimed in `src/`; `SUBCOMMANDS` is consumed only by `__main__` and `test_dispatcher_cli.py` (localdev hits are the symlink mirror); `test_packaging.py` enumerates neither modules nor subcommands; REUSE.toml globs (`skills/**/*.py`, `skills/**/tests/**` AGPL re-assert) cover both new files with no annotation change; `stockroom.warehouse` import for `home_dir()` pulls duckdb only at schedule runtime (dispatcher row is lazy, matching migrate/query); no crontab/launchctl/plistlib logic exists anywhere to conflict with
    - Live facts gathered: this machine's cron daemon is running and named `cron` (`pgrep -x cron` → pid), `crontab` at `/usr/bin/crontab`, real crontab has ~24 lines of foreign entries (the live-validation backup protocol is not optional)
* Decisions made
    - Two fixable-in-place plan amendments: the daemon-check default matches `cron` or `crond` (distro name variance, B7); `schedule status` on the cron platform also reports a `daemon: running|not running` fact line (B9) — facts-only per the `doctor probe` convention, making "the environment is the state" re-entry honest about a schedule that exists but cannot fire
    - No blocking findings; no advisory items withheld from the plan
* Insights
    - The B16 dispatcher extension stays mechanical (tuple + `--time` fingerprint), the third row added this way — the fingerprint-table shape from m1 keeps paying

## 2026-07-08 - PLAN (AMENDED AT GATE) - COMPLETE

* Work completed
    - Operator review at the preflight→build gate examined the nightly-log strategy against the operator's live cursor-warehouse cron entry (per-command `>> /tmp/*.log` routing); analysis delivered and accepted in whole, folded into `tasks.md` (B9/B12) and the creative doc — no component or dependency changes, preflight PASS stands
* Decisions made
    - **Log destination stays `~/.stockroom/logs/nightly.log`** (append, combined): `/tmp` is the most volatile dir on both targets (WSL wipes it every restart, macOS cleans ~3-day-old files) and the nightly log is the only witness that unattended freshness works; at ~3 quiet lines/night, append-forever is ~40 KB/decade and preserves the "failing since Tuesday" history a truncate-per-run log destroys
    - **`schedule status` gains a `log:` fact line on both platforms** (B9/B12): "where are the logs?" is answered by the same command that answers "is it installed?" — discoverability is structural, never memorized
    - Combined log over the operator's per-command split — at this volume the chronological story reads better and the failed phase is obvious from content; recorded as a coin-flip, not a hill
* Insights
    - Unredirected cron output is *mailed*, and MTA-less boxes (WSL default) discard it with only a syslog note — explicit redirection is the only way scheduler output survives at all, on either platform (launchd defaults to /dev/null without `StandardOutPath`/`StandardErrorPath`)

## 2026-07-09 - BUILD - COMPLETE

* Work completed
    - All six plan steps, each TDD red→green: `stockroom.schedule` (payload renderer + `parse_time`, cron managed-block half, launchd owned-plist half, platform-dispatched flat CLI), eighth dispatcher row, `test_schedule.py` (30 tests) + `test_schedule_cli.py` (3) + dispatcher tuple/fingerprint extension — 362 passed, 3 torch-gated skips, `make ci` green end to end
    - `sr-initialize` SKILL.md Steps 8–9 replace the "What's next" stub (scheduling consent/install/relay; first run + count sanity-check), every example executed live before being written in; README, techContext, systemPatterns accreted
    - Live validation on this WSL box against the real crontab (backed up first, 24 foreign lines): install/re-install/`--time`/remove/no-op all verified with byte-for-byte foreign-line diffs; daemon `cron` running → `daemon: running` fact, no warning
    - First run through the shim: `stockroom ingest --full` (11 min, 809 sessions, 29 080 messages) → `stockroom embed` (48 min, 39 805 chunk vectors) → count sanity-check green → re-run `embed` no-op (incrementality confirmed). The operator's warehouse is populated, embedded, and query-ready with nightly freshness scheduled at 03:30
* Decisions made
    - **Payload gained subshell parentheses** (`(date; … && …) >> log 2>&1`): live validation exposed that the creative doc's unparenthesized form binds the redirection only to the final `&&` operand — date output and ingest failures would be mailed and discarded. Test-first fix; B1 now pins the exact payload string; launchd reuses the identical payload with plist Standard*Path as backstop
    - Entry `PATH=` prefix: shim dir + uv dir (deduped) + `/usr/bin:/bin`; `--time` malformed input → argparse-clean exit 2 naming `HH:MM`
* Insights
    - `make sync` (and thus `make test`/`make ci`) strips out-of-lock torch *every* run — a dev-box embed must be preceded by `make torch` whenever CI ran in between; the nightly job is immune (shim runs `--no-sync`)
    - The one plan deviation was exactly where the plan predicted risk concentrates: the cron execution environment (redirection semantics), not the Python

## 2026-07-09 - QA - COMPLETE (PASS)

* Work completed
    - Semantic review of `stockroom.schedule` + tests + prose against the plan (KISS/DRY/YAGNI/completeness/regression/integrity/documentation): B1–B17 all implemented and test-pinned, both halves share one payload renderer / PATH resolver / shim guard, dispatcher row and flat-parser conventions match doctor/shim exactly, docs accreted everywhere the plan named
    - One trivial fix applied: dead `isinstance(args.time, tuple)` fallback in `main` removed — argparse applies `type=` to string defaults too (verified live), so `args.time` is always a validated tuple; full suite re-run green after (364 passed, 1 skipped — torch present, so the real-model tests ran)
* Decisions made
    - PASS written to `.qa-validation-status`; no substantive findings, nothing routed back to Build or Plan
* Insights
    - The two inline `assert`s (payload `%`-free, payload quote-free) are invariant pins in the style of the golden-snapshot discipline — they guard never-do list items at the exact point of construction, complementing the tests that pin the same facts from outside

## 2026-07-09 - REFLECT - COMPLETE

* Work completed
    - Full-lifecycle reflection written to `memory-bank/active/reflection/reflection-p3-m4-sr-initialize-scheduling.md`; persistent files reconciled (techContext/systemPatterns already updated during build; productContext untouched — nothing invalidated)
* Decisions made
    - launchd artisanal validation on the M4 stays a post-milestone operator step (m3 precedent), not a blocker
* Insights
    - Pin generated output exactly, not by fragments — B1's substring assertions let a semantically-wrong payload pass until live validation caught it; the golden-snapshot lesson holds at single-line scale
    - Example shell lines in creative docs are untested code: when promoted into a plan they deserve the same suspicion — "every example executed live first" is the guard that worked
