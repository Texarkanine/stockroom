---
task_id: dashboard-subagent-pills
date: 2026-08-26
complexity_level: 3
---

# Reflection: dashboard-subagent-pills

## Summary

The dashboard session view now shows warehouse-linked subagent sessions as sibling inset pills (`#msg-{ordinal}-sa-{n}`) and a `parent:` line on child views. Build followed the re-plan; QA passed with no blocking findings; live UAT on the motivating Cursor pair placed the one typed spawn on turn 48 and omitted the untyped nudge.

## Requirements vs Outcome

Delivered as specified. Existing `#msg-N` stays exclusive; new spawn fragments are a sibling parser. Claude unmatched spawn ids are omitted. Cursor places only via aligned zip or unique `agent_type` pairs. JSON export keeps `messages[].subagents` and `parent_spawn`; markdown stays pill-free. Sessions list is still top-level. No schema or ingest change.

Nothing material was added beyond the plan. The live parent’s untyped Task at msg 55 produces no pill — that is the slot rule, not a gap.

## Plan Accuracy

The **first** plan was not buildable. Preflight `FAIL (blocking)` was right: leftover needed parent message ordinals the helper did not take; `hashchange` only accepted `#msg-N`; JSON export is identity stringify; unit 4 had no failing render test because `dashboard.mjs` has no DOM harness.

The **re-plan** (five units, render model before mount, omit unmatched Claude, JSON keeps fields) was the sequence that shipped. File list and TDD order held. The operator then forbade leftover entirely; that narrowing was already in `tasks.md` when Build started, so the units did not need reordering.

Surprises were operational, not design: this machine’s live dashboard stays on `:58008`, so UAT used `:58018`. Browser-tool click on `parent:` focused the link but did not navigate; href + hash boot did.

## Creative Phase Review

**Spawn association (option C, then operator amendment).** Claude join and Cursor typed-Task slots held. The original leftover-on-last-Task honesty compromise did **not** hold: a pill is a positive claim, so leftover and shifting zip are forbidden. That amendment is the load-bearing design, not a polish. Residual risk (two compensating holes, one shared type) was left documented — no warehouse signal to close it.

**Pill chrome (option B).** Sibling inset + heading-as-single-link + `parent:` under metadata translated cleanly. The sketch’s extra “Open conversation” line was correctly dropped (creative already preferred one focusable link). Pills cannot live inside `#msg-N` if `#msg-N-sa-M` must scroll to the pill — that constraint survived implementation.

## Build & QA Observations

Build was the planned TDD walk. Association and payload tests carried the policy; JS model tests carried sibling insertion and parent-line visibility before any `dashboard.mjs` / `index.html` edit. Mount itself remains untested at the DOM layer — live UAT was the check that `#session-parent` clears, pills are siblings, and hash boot lands on the pill.

QA passed clean. It did not find a plan/implementation gap; preflight and the operator’s omit rule had already removed the places a guessed turn could hide.

## Cross-Phase Analysis

Preflight’s blocking findings would have been expensive in Build: leftover without `message_ordinals` is an API lie; a spawn hash that `hashchange` ignores looks like a broken deep link; a render unit with no red test is a CSS tweak waiting to nest pills inside `#msg-N`.

The second preflight (`PASS WITH ADVISORY`) still described leftover. The operator then narrowed the policy. Build proceeded without a third preflight because the change **removed** surfaces (no leftover, no `message_ordinals`) rather than adding them. That was safe here; it would not have been safe if leftover had been *added* after advisory.

Creative leftover and the first plan’s “best-effort pill” were the same mistake: treating a missing child as something the UI must still point at. The operator’s rule (omit rather than guess) is the one the tests now encode.

## Insights

### Technical
- Cursor `source_mtime` on parent and child can be identical; time-proximity matching is not available. Association is provenance (Claude) or corroborated slot/type (Cursor), nothing else.
- An untyped parent `Task` is not a spawn slot — same rule as ingest `_parent_subagent_types`. The live “Nudge L3 QA” at msg 55 is the motivating example, not a bug.
- When `dashboard.mjs` has no DOM harness, a pure item list in `dashboard-session.mjs` is the existing-suite way to specify sibling insertion and parent-line visibility before production mount.
- `source_tool_use_id` stays off public `tool_calls` JSON; Claude join is a server-side provenance use of that column, not a new warehouse identity key.

### Process
- A dashboard unit that only edits `dashboard.mjs` / `index.html` is not TDD until a testable model (or a real DOM harness) goes red first. Preflight was right to block the first unit 4.
- Narrowing association after an advisory preflight (omit more, add nothing) did not need another gate. Widening it would have.
- Live UAT of this dashboard on a machine that already serves `:58008` must use a second port. Do not rectify the shim or restart the standing listener from a parallel worktree.
