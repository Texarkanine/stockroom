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

---

# Rework round 1: PR #142 review fixes (2026-10-16)

## Summary

All six bot inline comments on PR #142 were valid and are fixed. Under `--plugin-dir`, no checkout is labelled `claude` because of where its path sits. Step 7 covers synced copies and engines that cannot be checked. `rectify` and `install` no longer raise on such engines. The printed Step 2 line is shell-quoted. QA PASS; `make ci` green (pytest 946 passed, 23 skipped).

## Requirements vs Outcome

All six findings were delivered, plus brief AC7 to AC9.

- The operator added one constraint after the first rework plan: no Claude-driven questions for Cursor users.
- So outside the default plugins folders only Claude Code asks; Cursor keeps its first-pass evidence (`CURSOR_PLUGIN_ROOT`).
- One Cursor outcome changes without a new question: a claude.ai-synced copy read from Cursor is now `claude`, not `dev`.
- Accepted residual: a Cursor checkout whose real path is cache-shaped still gets `cursor`.
- Deferred to the operator: preflight's idea of letting the version folder prove an install.

## Plan Accuracy

- The first rework plan broke a constraint nobody had stated: its cost line put a question on Cursor users. Because that line said so in plain words, the operator caught it before Build. One revision fixed it.
- Prototyping the Step 2 block before writing the plan held up: the red sets in Build matched the plan exactly.
- **Surprise:** Cursor agents on this machine read skills from Claude Code's plugin folders (25 reads in the warehouse). So a path rule written for Claude also decides Cursor outcomes.

## Build & QA Observations

- Build was linear: two executable units went red, then green, and one format-check line wrap was fixed.
- QA found a regression from this round: replacing `Path.is_file()` with a direct `stat` lost its `ValueError` catch, so a NUL byte in a header raised. It was fixed test-first after QA, together with four wording fixes.
- I filtered test-run output twice (`grep`, `sed`), which the test-running rules forbid. The summaries I read were complete, but the rule is about reading the whole output.

## Insights

### Technical

- **When replacing a stdlib convenience with the call underneath it, carry over every implicit catch.** `Path.is_file()` swallowed ENOENT-family errors and `ValueError`; listing the errnos covered only the first. Read the replaced function's `except` clauses, on every supported Python, before writing the replacement.
- **Judge a heuristic by which way it fails.** A wrong `dev` is caught, because Step 7 stops when `APP_DIR` is not the user's checkout. A wrong harness label is silent. Point uncertain branches toward the caught side.
- **Test the interface the agent consumes.** Reading results back through the printed line, not the block's variables, is what exposes quoting defects.

### Process

- **Put a plain-words cost line on every design choice in a plan.** It let the operator veto the Cursor question before any code was written.
- **Bots found four real path-shape edge cases that the first QA passed.** For path heuristics, QA should try hostile paths (`synced`, `cache/<a>/<b>`, quotes), as this round's QA did.

### Million-Dollar Question

This is still the first pass's answer: one engine-side classifier of the install kind. Preflight's version-folder proof sharpens it. Claude Code names the copy's folder after the manifest version and Cursor after the clone's commit, so the copy can prove it is an install without asking anyone or trusting substitution. That would remove the Claude Code question and the Cursor residual. It needs the operator's call, because it replaces a question they accepted.
