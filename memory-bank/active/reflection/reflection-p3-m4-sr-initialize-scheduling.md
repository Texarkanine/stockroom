---
task_id: p3-m4-sr-initialize-scheduling
date: 2026-07-09
complexity_level: 3
---

# Reflection: sr-initialize — scheduling and first run

## Summary

Built `stockroom.schedule` (the dispatcher's eighth subcommand: `install | status | remove` over cron and launchd) plus `sr-initialize` Steps 8–9, and closed the milestone with a real first run: the operator's warehouse is populated (809 sessions, 29 080 messages), embedded (39 805 vectors), and refreshed nightly at 03:30 by a live cron entry. All 17 planned behaviors are test-pinned; QA passed with one trivial fix.

## Requirements vs Outcome

Every milestone requirement delivered: nightly ingest + embed installed via cron with idempotent re-install semantics (launchd half unit-tested, M4 validation deferred to the operator per the m3 precedent), entries invoking the shim by name with install-time-resolved `PATH=`, judgment (consent, time-of-night) in skill prose, and a first full ingest + embed leaving a query-ready warehouse. Nothing dropped or descoped. One addition beyond the plan text: subshell parentheses in the payload (see Plan Accuracy) — a correctness fix, not scope creep.

## Plan Accuracy

The plan's sequence, file list, and test inventory were exactly right — six steps executed in order with no reordering, and the B1–B17 behavior list mapped one-to-one onto the shipped tests. The plan also predicted correctly *where* the risk lived: "the milestone's real risk concentrates in the cron execution environment, not the Python." That is precisely where the one deviation surfaced: the creative doc's payload `date; stockroom ingest && stockroom embed >> log 2>&1` binds the redirection only to the final `&&` operand — `date` output and any ingest failure would be mailed and discarded, silently defeating the log's entire purpose (being the witness that unattended freshness works). Live validation caught it; the fix (wrap the command list in a subshell) was test-first and B1 now pins the exact payload string.

A second unplanned wrinkle: `make ci` strips out-of-lock torch *every* run (by design), which broke the first-run `stockroom embed` mid-milestone and required a re-provision. Known contract, but the plan's step 6 ordering (gate *and* first run in the same step) made the interaction easy to trip over.

## Creative Phase Review

The architecture decision (Option A: flat `stockroom.schedule`, managed crontab block, owned plist, shared payload renderer, judgment-in-prose) held up completely — no friction translating it to code, and the foreign-line-preservation logic it insisted on putting under tests survived contact with the operator's real 24-line crontab byte-for-byte on every mutate step. The one blemish: the creative doc's *concrete example entry* carried the redirection-binding bug. The design was right; the illustrative shell line inside it was wrong, and the plan inherited it verbatim. Worth noting the never-do list and quality-attribute ranking did their job — "correctness under the drift/staleness posture" is exactly the axis on which the bug was caught.

## Build & QA Observations

Build was smooth: all four engine steps went red→green without iteration, and the established seams (`smi_runner` precedent, subprocess CLI convention, dispatcher fingerprint table) made the test infrastructure feel prefabricated. The live-validation protocol (backup first, diff foreign lines after every step) turned the scariest operation — mutating the operator's real crontab — into a mechanical checklist. QA found one trivial dead branch (argparse applies `type=` to string defaults, so the `isinstance` fallback in `main` was unreachable) and nothing substantive.

## Cross-Phase Analysis

The causal chain worth tracing: creative doc example → plan pinned tests to substrings of it (B1 asserted fragments, not the whole line) → build implemented it faithfully → the *live-validation step the plan itself mandated* caught what the unit tests could not, because the tests were only as strict as the example they encoded. The corrective ripple was healthy: B1 went from substring assertions to pinning the exact payload string, and the launchd plist test now asserts payload identity with `render_payload` rather than a lookalike. Preflight's live facts (daemon named `cron`, running; ~24 foreign crontab lines) were directly load-bearing during validation — no surprises came from anything preflight had already probed.

## Insights

### Technical

- POSIX redirection binds to the last simple command in an `&&`/`;` list, not the list — any rendered "compound command + redirection" line needs subshell parentheses (or the redirection is partial). This is now asserted at construction (`render_payload`) and pinned exactly in B1.
- argparse applies `type=` to *string* defaults too — a `type`-validating flag with a string default never yields the raw string, so post-parse re-validation fallbacks are dead code by construction.
- When a test pins generated output, pin the exact string, not fragments: every substring assertion is a place where a semantically-wrong render can still pass. Same lesson the golden-snapshot discipline already teaches at file scale, now confirmed at single-line scale.

### Process

- "Every example executed live before being written in" (the SKILL.md rule) plus "live-validate rendered artifacts on the real machine" is what actually catches example-inherited bugs — the illustrative shell line in a creative doc is untested code and should be treated with the same suspicion as any other untested code when it gets promoted into a plan.
- On a dev box, any workflow that interleaves `make ci` (or `make test`/`make sync`) with a torch-dependent run must re-run `make torch` in between; the exact-sync-strips-torch contract is per-invocation, not per-session. The nightly job is immune (shim runs `--no-sync`), which is itself a nice confirmation the torch-safe contract lives in the right place.
