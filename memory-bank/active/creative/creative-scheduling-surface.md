# Architecture Decision: Scheduling Logic Surface & Idempotent Entry Management

## Requirements & Constraints

Functional: install a nightly ingest + embed schedule via cron (Linux/WSL) or launchd (macOS); idempotent re-install; removable; the skill must be able to re-probe scheduled state ("the environment is the state").

Quality attributes, ranked:

1. **Correctness under the drift/staleness posture** — no rendered-out artifact may carry a raw engine path; entries invoke the shim (`stockroom ingest` / `stockroom embed`). A wrong or stale entry silently kills freshness, the product's primary mechanism.
2. **Testability** — idempotency and foreign-line preservation are exactly the kind of logic that must be TDD-covered; prose cannot be.
3. **Simplicity** — two platforms, one entry, no scheduler abstraction layer.

Technical constraints (cross-milestone invariants):

- The dispatcher owns all logic; the shim and every rendered artifact stay dumb.
- The scheduler's execution environment is hostile: cron runs with `PATH=/usr/bin:/bin` (no `~/.local/bin`, so neither the shim nor `uv` resolves by name), `%` is cron-syntax, and launchd inherits no login shell environment. Per-machine absolute-path resolution at install time is the roadmap's explicitly named hazard.
- Windows-native scheduling is out of v1 (WSL = the Linux/cron path).
- Errmsg ratchet: every failure names the next action.

Never-do list (leading with it, per the m2/m3 process insight):

- **Never bake a raw engine path into a scheduler entry** — the shim is the only file allowed to know `APP_DIR`.
- **Never touch a crontab line we did not write** — the operator's crontab has decades of real entries; clobbering one is unrecoverable.
- **Never leave two stockroom entries behind** — re-install must replace, not accumulate.
- **Never assume the scheduler's PATH** — resolve the uv dir and the shim dir at install time and bake them into the entry's own `PATH=` prefix.
- **Never install silently against a dead scheduler** — a WSL box without a running cron daemon gets a warning naming the fix, not a green report.

Scope boundary: the nightly *content* is fixed by the milestone (`stockroom ingest` then `stockroom embed`); this decision is about where the install/manage logic lives and how idempotency works. The session-start hook is out of scope (dashboard phase; hooks never ingest).

## Components

- `stockroom.shim` (m2): renders/installs the on-path launcher — the thing the entries invoke.
- `stockroom.doctor` (m3): read-only probe/smoke — the precedent for the facts-vs-judgment split.
- `stockroom.__main__`: the dispatcher; each new surface is one `SUBCOMMANDS` row.
- `skills/sr-initialize/SKILL.md`: the judgment/consent layer — asks the user, relays reports.
- The system crontab / `~/Library/LaunchAgents/` — state *outside* the repo, shared with foreign entries (crontab) or file-owned by us (launchd plist).

## Options Evaluated

- **Option A — new `stockroom.schedule` module** (eighth subcommand: `install | status | remove`): all crontab/plist manipulation in tested Python behind injectable runners; skill prose owns consent (the schedule time, whether to install at all) and relays reports.
- **Option B — prose-only**: the skill edits the crontab / writes the plist with shell commands directly.
- **Option C — extend `stockroom.shim`**: scheduling as another "rendered-out artifact" action on the existing module (`shim schedule …`).

## Analysis

| Criterion | A: `stockroom.schedule` | B: prose-only | C: extend `shim` |
|-----------|------------------------|---------------|------------------|
| Fitness | Full: install/status/remove, both platforms | Install only; status/remove ad hoc | Full, but under a misnamed surface |
| Testability | TDD with injected `crontab`/`launchctl` runners | Untestable — the never-do list lives in prose | Same as A |
| Simplicity | One new flat module, mirrors `doctor`/`shim` | No new code, but idempotency logic in prose is *harder* | Couples two unrelated lifecycles |
| Maintainability | Single responsibility; m5+ can call `schedule status` | Drift-prone (the incantation-garden failure mode reborn) | `shim`'s ownership policy and cron filtering interleave |
| Risk | Low; blast radius = one module | High: a prose bug edits the operator's real crontab | Medium: policy entanglement |

Key insights:

- The foreign-line-preservation requirement alone decides it: filtering someone's live crontab is precision logic with an unrecoverable failure mode — exactly what the workspace TDD rule exists for. Option B violates constraint "the dispatcher owns all logic" and never-do #2's testability demand simultaneously.
- Option C fails on lifecycle: the shim is rewritten by hooks on every session start; schedule entries are written once with consent. Different owners, different cadences, different idempotency mechanisms — one module would carry two policies.
- This is the third application of the established judgment-vs-mechanism split (search: m6; onboarding: m3; scheduling: now). Mechanism (entry rendering, filtering, platform dispatch, PATH resolution) is engine Python; judgment (consent to install, the schedule time, takeover of scheduling on a machine that already has some other freshness mechanism) is skill prose.

## Decision

**Selected**: Option A — a new flat `stockroom.schedule` module, the dispatcher's eighth subcommand, with `install | status | remove` actions.

**Rationale**: it is the only option that puts the unrecoverable-failure logic (foreign crontab lines) under tests, it matches every established pattern (flat module + injectable seams + one `SUBCOMMANDS` row + skill-prose judgment), and `status` is what makes `sr-initialize`'s "the environment is the state" re-entry contract real for scheduling.

**Tradeoff**: a third rendered-artifact writer to keep coherent (shim, hooks config, now schedule entries) — accepted because each has exactly one tested owner module.

## Implementation Notes

### Platform dispatch

`platform.system()` → `Linux` = cron, `Darwin` = launchd, anything else = exit 1 naming WSL as the Windows path. Injectable (`system` kwarg) for tests.

### Cron: marker-delimited managed block

Idempotency mechanism (same shape as the Makefile's localdev pre-commit-hook markers, proven in this repo):

```text
# BEGIN stockroom nightly (managed by 'stockroom schedule' - do not edit)
30 3 * * * PATH=<uv-dir>:<shim-dir>:/usr/bin:/bin /bin/sh -c 'date; stockroom ingest && stockroom embed' >> <home>/.stockroom/logs/nightly.log 2>&1
# END stockroom nightly
```

(The `/bin/sh -c` wrapper is load-bearing: a POSIX variable assignment may only prefix a *simple* command, so the `PATH=` prefix cannot sit directly before a brace group or an `&&` list.)

- Read `crontab -l` (a missing crontab — exit 1 "no crontab for user" — is an empty one, not an error), strip any existing marker-delimited block, append the fresh block, write back via `crontab -`. Install = filter + append; remove = filter only; both idempotent by construction. Foreign lines pass through byte-for-byte.
- The command invokes the shim **by name** — the `PATH=` prefix (uv's dir and the shim's dir resolved at install time via `shutil.which`, absolute) is what makes that resolve under cron's minimal environment. No engine path appears anywhere.
- `%` is newline in crontab syntax: the rendered command must contain none (bare `date`, no format string) and a test pins that.
- Logs append to `~/.stockroom/logs/nightly.log` (`STOCKROOM_HOME`-aware); output is a few lines per night, rotation is YAGNI.
- If `shutil.which("stockroom")` fails, install refuses with the ratchet remedy (bind the shim first — `sr-initialize` step 7). If the cron daemon isn't running (injectable check, e.g. `pgrep -x cron`), install still writes but the report carries a warning naming the fix (WSL: `sudo service cron start` / enable systemd) — never a silent green.
- `crontab` interaction is one injectable runner seam (`argv -> stdout`, raising on failure), mirroring `doctor`'s `smi_runner`.

### launchd: an owned plist file

`~/Library/LaunchAgents/com.stockroom.nightly.plist` (dir injectable): idempotency is file ownership — write the plist (stdlib `plistlib`), then reload via an injectable `launchctl` runner (`bootout` ignoring not-loaded failures, then `bootstrap gui/<uid>`). Remove = bootout + delete, no-op when absent. `ProgramArguments` = `/bin/sh -c '<the same rendered command>'`; PATH rides in `EnvironmentVariables` instead of an inline prefix; `StartCalendarInterval` carries Hour/Minute; stdout/stderr paths point at the same log.

### Shared command rendering

One function renders the `date; stockroom ingest && stockroom embed` payload (and its log redirection) used by both platforms — the entry content is decided once.

### CLI shape

Flat parser like `shim`/`doctor`: `stockroom schedule {install|status|remove} [--time HH:MM]` (default `03:30`, validated). `status` prints `installed: <schedule line / plist label + interval>` or `not installed` and exits 0 either way (facts, not errors — the `doctor probe` convention).

### Judgment stays in prose

`sr-initialize` asks the user before installing (time-of-night is a human choice with a recommended default), relays the daemon warning verbatim, and skips the step when `status` says installed. First-run orchestration (`stockroom ingest --full`, `stockroom embed`, a count-query sanity check) is prose over the shim — no new engine code.
