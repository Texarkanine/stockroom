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
