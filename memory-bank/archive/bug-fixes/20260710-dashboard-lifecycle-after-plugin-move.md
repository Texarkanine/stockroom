---
task_id: dashboard-lifecycle-after-plugin-move
complexity_level: 2
date: 2026-07-10
status: completed
---

# TASK ARCHIVE: dashboard-lifecycle-after-plugin-move

## SUMMARY

After plugin-root move, heal already updated the shim/env, but a detached dashboard from the old engine kept port 6767. Extended `stockroom dashboard` with start-time identity-aware replace (creative Option B): record owned listener identity under stockroom home; on launch, replace when owned-but-stale; never stop-on-close; never kill foreign listeners. Shipped in [#20](https://github.com/Texarkanine/stockroom/pull/20).

## REQUIREMENTS

1. After one hook/session cycle that heals the shim to a new engine dir, the process on `http://127.0.0.1:6767/` must be that new engine — not a leftover from a dead plugin path.
2. Multi-harness: closing one harness must not stop the dashboard.
3. Preserve the hook contract: idempotent, fire-and-forget, never errors.
4. Do not kill unrelated listeners on 6767.
5. Implement per creative Option B: start-time identity-aware replace in the launcher (not close hooks).

## IMPLEMENTATION

### Design decision (inlined from creative)

Evaluated close/stop hooks (A), start-time identity-aware replace (B), cooperative self-exit stamp (C), and refcounted harness leases (D). **Selected B**: the dashboard is a machine singleton; the bug was "port probe equates any listener with a current listener." Fix identity at the place that already runs after every heal. Close hooks fail multi-harness safety and lack a reliable IDE-lifetime signal on Cursor.

### Core mechanisms

| Piece | Behavior |
| --- | --- |
| Identity record | Port-scoped file under stockroom home: `pid`, absolute `app_dir`, `__version__`, `port` |
| Decision matrix | Free → spawn; same identity → noop; stale owned + verified → SIGTERM/wait/spawn; foreign/unknown → leave alone |
| Kill safety | Only SIGTERM the pid from our identity file after `verify_owned` (cmdline /proc when available) |
| Degrade | Kill/wait failure → print URL, exit 0 (hook contract) |
| Bind write | Foreground successful bind writes identity; soft-fail on OSError so serve still proceeds |

### Key files

| Area | Files |
| --- | --- |
| Identity | `skills/sr-search/src/stockroom/dashboard/identity.py` |
| Launcher | `skills/sr-search/src/stockroom/dashboard/__main__.py` |
| Docs | `docs/using.md` |
| Tests | `test_dashboard_identity.py`, `test_dashboard_cli.py` |

### Accepted residual

Pre-identity leftover dashboards cannot be proven owned → one-shot manual kill; after first successful new launch, identity exists and future moves heal.

## TESTING

- TDD: B1–B8 (free / same / stale owned / foreign / kill failure / identity write / EADDRINUSE / helpers).
- Full suite: **467 passed, 3 skipped**; ruff clean.
- `/niko-qa` semantic review PASS (trivial test polish only).

## LESSONS LEARNED

### Technical

- Port probe alone is not identity; a durable home record (like torch freeze) is the right companion for disposable plugin trees.
- Only SIGTERM the pid we wrote, after cmdline verify — never hunt by port.
- Package `__version__` may lag marketplace version; `app_dir` remains the primary staleness signal after plugin hash moves.

### Process

- Standing creative before `/niko` made L2 plan/build almost mechanical; keep that order for “last mile” reliability gaps after a related fix lands.

### Million-dollar question

If identity-aware replace had been assumed when the dashboard launcher was first designed, it would still be the same shape: probe → classify by home identity → reuse/replace/leave, with the OS bind as the spawn race mutex. Close-hook lifecycle remains the wrong model for a machine singleton.

## PROCESS IMPROVEMENTS

For post-fix reliability gaps that need an architecture call, run creative before `/niko` so plan/build stay mechanical.

## TECHNICAL IMPROVEMENTS

None beyond the accepted pre-identity one-shot manual kill documented in `docs/using.md`.

## NEXT STEPS

None. Task complete and archived.
