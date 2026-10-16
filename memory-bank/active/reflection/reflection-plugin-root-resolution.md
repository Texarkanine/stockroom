---
task_id: plugin-root-resolution
date: 2026-10-16
complexity_level: 2
---

# Reflection: plugin-root-resolution

## Summary

`sr-initialize` now finds the engine and shim owner without plugin-root environment variables. A marketplace install, meaning a harness cache copy or a claude.ai-synced copy, gets its harness label, and every checkout-based load gets `dev`. `shim rectify` now replaces a dead shim of any owner, so leaving dev never strands the on-path command. QA passed, and an end-to-end run on real Claude Code 2.1.301 confirmed the shipped text resolves correctly.

## Requirements vs Outcome

Every requirement was delivered.

- The hook audit found no fault, so the hooks are unchanged.
- Two additions came from the operator mid-plan: "contributors always get `dev`", and `rectify` replacing dead shims, which relaxed Constraint 4 with approval.
- Dropped by operator decision: option B (dev-load rectify no-op), option E (separate dev data), and the argument-substitution guards.
- Cursor's agent-shell behavior is still undocumented. The design does not depend on it, and a UAT line is left for the operator.

## Plan Accuracy

The first plan had the right diagnosis but the wrong owner rule. It labelled `claude --plugin-dir` as `claude`, and it relied on a `.claude`/`.cursor` path rule that misses `CLAUDE_CODE_PLUGIN_CACHE_DIR`. Three preflights and one operator round reshaped it:

- **Preflight 1:** the mirror path, and takeover offers on healthy shims.
- **Preflight 2:** `$N` / `$ARGUMENTS` substitution.
- **Operator:** dev semantics.
- **Preflight 3:** synced plugins, and Step 7 reading the shim off PATH.

The challenges that actually bit were layout facts: caches containing `.git` and `Makefile`, and `--plugin-dir` silently replacing the installed plugin. None of them was a technology risk.

## Build & QA Observations

The build was linear and clean: every unit went red, then green, and a mutation check confirmed the Step 2 test catches a regression to an unbraced token. `make ci` cannot pass end to end on this machine, because local uv 0.8.22 trips the lock checks. They pass under CI's pinned uv 0.12.22.

QA passed with one real edge case: a localdev mirror in a repo cloned into a directory named `cache` read as an installed plugin. It was fixed test-first by also requiring the `<root>/skills/sr-search` layout. Five wording and doc nits were fixed alongside.

## Insights

### Technical

- **Harnesses give plugin roots to hooks, never to agent shells.** For Claude Code, the only channel into a skill is skill-text substitution, and it matches exact tokens only. A bare `$CLAUDE_PLUGIN_ROOT` or `${…:-x}` stays literal, as do `$N` and `$ARGUMENTS` when arguments are passed. Check any skill shell snippet against this before trusting it.
- **Marketplace copies are git clones that include the `Makefile`,** so checkout markers cannot tell dev from installed. The install layout can: `…/cache/<marketplace>/<plugin>/<version>/skills/sr-search`. And "defer to `make shim` from the repo root" silently succeeds inside a plugin cache.
- **Ownership keyed on labels made the one stuck path.** "Never touch a foreign shim" also froze dead ones. Keying the takeover on liveness (no `pyproject.toml`) keeps the label as a courtesy for working shims only.
- **Executing a shipped skill fence in tests works.** Run it as a real program under each shell, with the harness rendering modeled exactly as a probe verified, and mutation-check it. This catches skill regressions that wording asserts cannot.

### Process

- **Agents silently improvising around a broken skill hid this bug from plugin 0.1.1 to 2.1.1.** Warehouse transcripts proved it in minutes. When a skill step "works", check what the agent actually ran.
- **A cheap headless `claude -p` probe** (small model, throwaway plugin, read the session transcript) settled substitution semantics that the docs left ambiguous. Two probes changed the design.
- **Asking "is this a real risk under the documented flow?"** before changing shared hook policy turned a proposed hook change (B) into a narrower fix that keeps dev self-heal. The operator's mental model of entering and leaving dev was the real spec.

### Million-Dollar Question

The engine already knows where it lives (`shim.default_app_dir()`). If "the owner is a function of where the engine is installed" had been foundational, one tested Python function would classify the install kind from the engine's own path. A real install is a harness cache or synced copy, with the harness taken from the path or a passed hint; everything else is `dev`. `shim install --owner auto`, `doctor probe` (including flagging a mis-owned shim), and a read-only `shim triage` for Step 7 would all call it. The skill would carry one line, handing over Claude Code's substituted root only as a hint for custom plugins roots.

What we built is that rule in shell inside SKILL.md, the one place a pre-shim agent can run it, pinned by tests. Moving it into the engine is the natural next step if the rule grows.

Follow-up candidates:

- `doctor probe` mis-owned-shim fact
- `stockroom shim triage`
- zsh in CI (macOS runner)
- operator UAT in Cursor for `CURSOR_PLUGIN_ROOT` in agent shells
