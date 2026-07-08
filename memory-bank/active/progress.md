# Progress

Milestone m2 of L4 project `p3-onboarding-cli-scheduling`: build the bake-then-verify `stockroom` shim — a REUSE-covered shim template shipped in the engine plus tested generation/installation logic that writes `~/.local/bin/stockroom` with a baked `APP_DIR`, runtime verify-then-re-resolve staleness healing (deciding the plugin-update TODO), deterministic resolution order across coexisting harness caches, a clear one-line uv-missing failure, a PATH-membership check, dev-repo parity (`make shim` or equivalent), and the README ad-hoc-invocation section rewritten around `stockroom <subcommand>`. See `memory-bank/active/milestones.md` (m2) and `memory-bank/active/projectbrief.md`.

**Complexity:** Level 3

## 2026-07-08 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - `/niko` re-entry routed the L4 project through milestone advancement: m1 checked off, m1 sub-run ephemeral state deleted
    - m2 classified as Level 3: complete feature across multiple components (template, generation logic, staleness healing, resolution order, dev parity, docs) without system-wide architectural implications
    - Fresh sub-run ephemeral state written: `progress.md`, `activeContext.md`, stubbed `tasks.md`; `projectbrief.md` and `milestones.md` preserved
* Decisions made
    - Level 3 classification, matching the milestone's estimate — the open design decisions reserved to m2 (staleness detection/re-resolution, harness-cache resolution order, template location, uv-missing behavior, dev ergonomics) justify a creative phase
* Insights
    - m1's `--version` flag on the dispatcher was added specifically as the identity probe for this milestone's staleness verification — the shim design should build on it
    - Open design questions are enumerated in `planning/brainstorm/stockroom-on-path-cli.md`; the creative phase should treat that document as its input

## 2026-07-08 - CREATIVE - COMPLETE

* Work completed
    - Two open questions explored and resolved with high confidence, one creative document each:
      `creative-shim-staleness-resolution.md` (algorithm) and `creative-shim-generation-surface.md` (architecture)
    - Empirical survey of real harness cache layouts on this machine (Cursor sha-dirs + `local/`, Claude version-dirs + `installed_plugins.json`); cost measurements: bounded glob ≈ 6 ms vs `find -L` ≈ 2.2 s
* Decisions made
    - Q1: shim re-derives the engine dir on **every** invocation — bounded glob over a fixed ordered root list, candidates ranked by plugin-manifest `"version"` (`sort -V`), baked `APP_DIR` preferred on ties and used as fallback for unknown layouts; a bare existence check was rejected because a lingering old cache dir would pin the shim to an outdated engine
    - Q2: `stockroom.shim` module CLI as the dispatcher's sixth subcommand, template in-package at `src/stockroom/shim_template.sh`; `make shim` for dev parity; the brainstorm's speculative separate `stockroom-dev` shim rejected (YAGNI — pinned variant is a render-time mode)
    - `REUSE.toml` needs `skills/**/*.sh` added to the code-shaped AGPL re-assert list (shell is software, not prompt content)
* Insights
    - The engine `pyproject.toml` version is static (`0.0.0`); the release-please-synced plugin-manifest `"version"` is the only uniform, semantically-correct currency signal across all install shapes
    - All scan roots are `~`-relative, so the rendered shim is end-to-end testable as a subprocess with `HOME` pointed at a fixture tree

## 2026-07-08 - PLAN - COMPLETE

* Work completed
    - Component analysis: template (`src/stockroom/shim_template.sh`), `stockroom.shim` module (render/install/CLI), dispatcher sixth row, `Makefile` `shim` target, README rewrite, `REUSE.toml` `.sh` re-assert, techContext section
    - Test plan: 24 behaviors across four levels; three new test files (`test_shim.py`, `test_shim_runtime.py`, `test_shim_cli.py`) plus `test_dispatcher_cli.py` / `test_licensing.py` extensions; rendered-shim runtime behaviors exercised as a subprocess against a fixture `HOME` with a stub `uv`
    - Six-step ordered implementation plan written to `tasks.md`, each Python step an explicit red→green TDD cycle
* Decisions made
    - `sort -V` rejected for the template (not POSIX/macOS-portable) — numeric dot-field sort with a ranking regression test instead
    - Install-time `--version` verify is conditional on the dest dir being on `PATH` (m3 owns PATH remediation); runtime never pays a verify exec
* Insights
    - The m2 acceptance spine is one runtime test: baked dir *still exists* but a higher-versioned install exists elsewhere → the shim must pick the newer one

## 2026-07-08 - PREFLIGHT - COMPLETE (PASS)

* Work completed
    - TDD encoding, convention compliance, dependency impact, conflict detection, and completeness verified against the codebase; `.preflight-status` written PASS
    - Verified the dispatcher `_usage()` auto-sizes to a sixth subcommand row; `conftest.py` already provides `repo_root` for the licensing extension; nothing else consumes `SUBCOMMANDS`
    - Verified plugin name `stockroom` (the scan-root path segment) is pinned by `test_packaging.py` against both manifests
* Decisions made
    - No blocking amendments; one advisory recorded (machine-readable `stockroom shim --json` report deferred to m3 — no consumer exists yet, YAGNI)

## 2026-07-08 - PLAN (REWORK) - COMPLETE

* Work completed
    - Operator vetoed the always-scan runtime resolution at the preflight→build gate: hard constraint "the shim ALWAYS finds the right stockroom — succeed correctly or refuse, never guess"; also flagged layout-coupled root-list maintenance and supply-chain injection via version-string ranking
    - Verified both harnesses hand plugin hooks the authoritative install root (`CURSOR_PLUGIN_ROOT` — docs + staff confirmation + cursor-warehouse's live hooks.json on this machine; `CLAUDE_PLUGIN_ROOT` — docs; Claude retains the previous cache dir ~7 days post-update)
    - Q1 creative doc rewritten (supersedes scan design); Q2 notes revised; `tasks.md` plan rebuilt: 8 steps, hook artifacts in scope, packaging-contract tests for the hook wiring
* Decisions made
    - Baked-only succeed-or-refuse shim: uv check → baked-dir validity → exec; one-line owner-appropriate remedies; **no resolution logic anywhere in the shim**
    - Staleness healing via sessionStart hook `shim rectify` using the harness-provided plugin root (dashboard-hook discipline amended, operator-sanctioned: launch dashboard *and* rectify shim; still never errors/blocks)
    - Two-harness resolution via explicit ownership marker: single writer per shim; init declines against a live foreign shim; takeover only when the incumbent's baked dir is dead *and* `--takeover` is explicit; `make shim` owns `dev` shims that harness hooks never touch
    - Pinned/normal mode split collapsed — every shim is baked-only
* Insights
    - The env-var-delivered root eliminates harness-layout knowledge from every component (shim: none; rectify: root is an argument; only committed hooks.json touches `${*_PLUGIN_ROOT}` — the artifact those vars exist for)
    - Write path is now harness → plugin-shipped hook → tested engine → `~/.local/bin`; no ambient filesystem state can trigger or influence a shim write

## 2026-07-08 - PREFLIGHT (RE-RUN AFTER REWORK) - COMPLETE (PASS)

* Work completed
    - Re-verified the reworked plan: TDD ordering (steps 1–6 red-test-first), dual-hook-config convention (mirrors dual manifests), manifest-key addition safe against `test_packaging.py` subset check and release-please jsonpath, `hooks/*.json` covered by base AGPL annotation, milestone completeness (the "plugin-update TODO decided here" is decided — by the operator's design); `.preflight-status` re-written PASS
* Decisions made
    - None blocking
* Insights
    - `make localdev` mirrors only `skills/` — plugin-delivered hooks will not fire from a localdev mirror; live hook verification requires a real plugin install (recorded for the QA artisanal checklist)

## 2026-07-08 - BUILD - COMPLETE

* Work completed
    - All 8 plan steps, each an explicit red→green TDD cycle: REUSE `.sh` re-assert; `shim_template.sh` + `render`; runtime behaviors (rendered script as subprocess, fixture `HOME`, stub `uv`); install/rectify ownership policy; `stockroom.shim` CLI + dispatcher sixth row; dual hook configs + manifest pointers; `make shim`; docs (README ad-hoc rewrite, techContext shim section, systemPatterns hook-discipline amendment + shim pattern)
    - 30 new tests across `test_shim.py` / `test_shim_runtime.py` / `test_shim_cli.py`, plus extensions to `test_dispatcher_cli.py`, `test_licensing.py`, `test_packaging.py`; shared `stub_uv` fixture in `conftest.py`
    - Full suite 311 passed / 2 torch-skips; `make ci` green end to end (lock-check, ruff, pytest, `reuse lint` 190/190)
* Decisions made
    - Remedy strings baked into the template must avoid shell-active characters (backticks in the dev remedy were command-substituted by the rendered script's double-quoted `echo`; the one-line-stderr runtime test caught it)
    - Flat argparse (positional `install|rectify` + shared flags) instead of subparsers — single help page, preserves the module-owns-its-flags convention
    - Licensing gained a cheap pin test (`test_shell_inside_skill_resolves_agpl`) despite the plan's inspection-only stance — zero-cost drift protection
    - `make shim` deliberately has no `sync` dependency so installing the dev shim never strips out-of-band torch
* Insights
    - The stub-`uv`-prints-argv fixture makes the entire exec contract (baked `--project`, `PYTHONPATH`, `--no-sync`, `--no-config`, verbatim arg forwarding) assertable without uv, torch, or a real engine run — the same trick should serve m4's scheduler-entry verification
    - Claude and Cursor hook schemas differ in timeout units too (seconds vs milliseconds), not just shape — one more reason the dual-config pattern beats a shared file
