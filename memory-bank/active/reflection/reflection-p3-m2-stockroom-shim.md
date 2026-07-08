---
task_id: p3-m2-stockroom-shim
date: 2026-07-08
complexity_level: 3
---

# Reflection: p3-m2-stockroom-shim

## Summary

Built the on-path `stockroom` command: a REUSE-covered, baked-only, succeed-or-refuse POSIX-sh shim rendered by tested Python (`stockroom.shim`, the dispatcher's sixth subcommand), healed by owner-guarded sessionStart hook rectification in both harnesses, with `make shim` dev parity and the README rewritten around `stockroom <subcommand>`. Build was clean (all 8 steps red→green, one trivial QA fix), landing the operator's post-veto design faithfully.

## Requirements vs Outcome

Every milestone requirement shipped: template + generation/installation logic, staleness healing (the plugin-update TODO — decided as hook rectification, not runtime resolution), two-harness determinism (ownership marker + takeover policy), one-line uv-missing failure (exit 127), PATH-membership check with conditional `--version` verify, `make shim`, README rewrite. One small addition beyond the plan: a licensing pin test (`test_shell_inside_skill_resolves_agpl`) despite the plan's "inspection only" stance — zero-cost drift protection, kept. Nothing was dropped or reinterpreted.

## Plan Accuracy

The reworked 8-step plan was executed in order with no reordering, splitting, or added steps — the strongest plan-fidelity run of the project so far. The anticipated challenges (dual hook schemas, hook discipline, tests never touching real `~/.local/bin`) were exactly the ones that appeared, and each had its planned mitigation ready. The one genuine surprise came from a place the plan didn't name: shell metacharacters in *rendered text* (backticks in the dev remedy were command-substituted by the template's double-quoted `echo`). The planned test shape — "exactly one stderr line" — caught it immediately, which is itself evidence the test plan was pitched at the right level of strictness.

## Creative Phase Review

- **Q1 (staleness, revised: baked-only + hook rectification + ownership)**: held up with zero friction. The implementation notes translated 1:1 into code — the shim runtime is three checks and an exec; every policy branch in the notes became exactly one test. The *original* Q1 (always-scan, version-ranked) being vetoed at the preflight→build gate is the real lesson: the hard constraint ("never guess") existed in the operator's head from the start but was only surfaced by showing them a concrete design that violated it.
- **Q2 (generation surface, S1+T1)**: held up unchanged through the Q1 rework — good evidence the two questions were correctly factored as independent axes. `Path(__file__)`-relative template loading and the sixth `SUBCOMMANDS` row worked exactly as predicted; `_usage()` auto-sizing (verified in preflight) meant the dispatcher change was one line.

## Build & QA Observations

Smooth: the stub-`uv`-prints-argv fixture made the entire exec contract assertable torch-free in-process-cheap; the subprocess-CLI and repo-root-fixture conventions absorbed all three new test files without new infrastructure. The only iteration loop was the backtick command-substitution bug (one cycle) and two mechanical lint/format passes. QA found one trivial KISS item (`field(default="")` for a plain default) and nothing substantive — consistent with the project's pattern that a preflighted, TDD-encoded plan yields a near-clean QA.

## Cross-Phase Analysis

The dominant causal chain is *positive*: the operator's veto at the preflight→build gate forced a plan rework that made build trivial. The superseded scan design would have carried root-list maintenance, version-ranking logic, and a supply-chain surface into the template — sh code, the least testable layer. The replacement moved all policy into Python and left the template with three checks, which is why build friction was near zero: the rework relocated complexity from the untestable layer to the tested one. Secondary chain: preflight's verification that both harnesses deliver `*_PLUGIN_ROOT` to hooks (docs + live artifact on this machine) is what made the hook-config step a pure-artifact exercise instead of an empirical investigation mid-build.

## Insights

### Technical

- Text rendered into a double-quoted shell context is an injection surface even when you wrote it yourself: keep substitution values free of shell-active characters (backticks, `$`, `"`), and pin the output shape ("exactly one stderr line") so violations can't pass silently. Now noted on the remedy constants.
- The stub-executable-prints-argv fixture (`stub_uv`) is the cheapest way to lock an exec contract; m4's scheduler entries (cron/launchd invoking the shim) should reuse it rather than inventing scheduler-side verification.
- Cursor and Claude hook schemas differ in *timeout units* (ms vs s), not just JSON shape — a shared hook config was never viable; the dual-config-mirroring-dual-manifest pattern is load-bearing, not stylistic.

### Process

- A hard operator constraint ("never guess") surfaced only when a concrete violating design was presented at a gate. For decisions with security/trust flavor, the creative phase should explicitly ask "what must this component *never* do?" before optimizing among candidate algorithms — the veto cost a full plan+preflight rework that one question might have avoided.
- Moving complexity from an untestable layer (sh template) into the tested layer (Python policy) is a design *goal*, not just a preference — the rework demonstrated it converts build risk into ordinary TDD work.
