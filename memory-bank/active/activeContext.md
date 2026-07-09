# Active Context

## Current Task: p3-m4-sr-initialize-scheduling
**Phase:** PLAN - COMPLETE

## What Was Done
- Component analysis: `stockroom.schedule` (new: install/status/remove over cron + launchd), dispatcher eighth `SUBCOMMANDS` row, `sr-initialize` SKILL.md steps 8–9 (scheduling + first run), README/techContext/systemPatterns accretion; `warehouse.home_dir()` reused for the nightly log path; shim invoked by name in every entry
- One open question resolved with high confidence (`creative-scheduling-surface.md`): flat `stockroom.schedule` module; cron = marker-delimited managed crontab block, launchd = owned `com.stockroom.nightly.plist`; entries carry an install-time-resolved absolute `PATH=` prefix in a `/bin/sh -c` wrapper; judgment (consent, time-of-night, first run) in prose
- Test plan: 17 behaviors (B1–B17) — payload/`%`-guard/time validation, cron foreign-line preservation + idempotent re-install + daemon warning, launchd plist shape + idempotency, platform dispatch, CLI + dispatcher integration; new `test_schedule.py` / `test_schedule_cli.py`, extended `test_dispatcher_cli.py`
- Six-step ordered plan in `tasks.md`: payload → cron → launchd → dispatch/CLI (each red→green) → SKILL.md prose (live-verified examples) → docs + live validation (WSL/cron + first full ingest/embed) + `make ci`

## Key Constraints Carried Forward
- Never a raw engine path in an entry; never touch a foreign crontab line; never two managed blocks; never assume the scheduler's PATH; never install silently against a dead cron daemon
- Live validation backs up the operator's real crontab before any mutate step; launchd is unit-tested here and artisanally validated on the M4 (m3 precedent)

## Preflight Outcome
- PASS (`.preflight-status` written). Two in-place amendments: daemon check matches `cron`/`crond` (B7); `schedule status` reports a daemon liveness fact on the cron platform (B9). Verified live: this machine's daemon is `cron` (running), real crontab carries ~24 foreign lines — backup protocol mandatory.

## Next Step
- Operator gate: run `/niko-build` to start the build phase
