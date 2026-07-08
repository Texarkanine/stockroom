# Task: p3-m2-stockroom-shim

* Task ID: p3-m2-stockroom-shim
* Complexity: Level 3
* Type: feature

Milestone m2 of L4 project `p3-onboarding-cli-scheduling`: a REUSE-covered shim template shipped in the engine plus tested generation/installation logic that writes `~/.local/bin/stockroom` with a baked `APP_DIR`, runtime verify-then-re-resolve staleness healing, deterministic resolution order across coexisting harness caches, a clear one-line uv-missing failure, a PATH-membership check, dev-repo parity, and the README ad-hoc-invocation section rewritten around `stockroom <subcommand>`.

## Component Analysis (interim — plan in progress)

### Affected Components
- **Shim template** (new, location TBD by creative): POSIX-sh script; environment plumbing only (baked `APP_DIR`, verify/re-resolve, `PYTHONPATH`, `uv run --no-sync --no-config`, exec into `python -m stockroom`).
- **Generation/installation logic** (new, tested Python; surface TBD by creative): renders the template with a baked `APP_DIR`, installs to `~/.local/bin/stockroom` idempotently, checks PATH membership, reports.
- **`stockroom.__main__` dispatcher**: possibly gains a subcommand for shim generation (TBD by creative).
- **`Makefile`**: dev-repo parity target (`make shim` or equivalent).
- **`README.md`**: ad-hoc-invocation section rewritten around `stockroom <subcommand>`.
- **`REUSE.toml`**: shell templates under `skills/**` currently resolve PPL-S — code-shaped `.sh`/scripts paths must be re-asserted AGPL.

### Environment Facts (verified on this machine)
- Cursor cache: `~/.cursor/plugins/cache/<marketplace>/<plugin>/<git-sha>/`; unversioned dev installs under `~/.cursor/plugins/local/<plugin>/`.
- Claude cache: `~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/`; `~/.claude/plugins/installed_plugins.json` records each plugin's `installPath` (authoritative, includes local installs).
- The shim runs *outside* any harness (cron, bare shell): no `CURSOR_PLUGIN_ROOT`-style env available at shim runtime.

### Invariants & Constraints
- Torch-safe contract structural in the shim (`--no-sync --no-config`, never an exact sync).
- Shim does environment plumbing only; all logic lives in the tested dispatcher.
- Run-in-place packaging holds (`package = false`, no console-script entry points, no build step).
- Shim is the one self-healing owner of the baked path; no other rendered-out artifact carries a raw engine path.
- REUSE compliance: the shim template is a licensed artifact.

## Open Questions

- [x] **Q1 — Runtime staleness healing & resolution order** → Resolved: always-scan, version-ranked, baked-preferred-on-ties selection over a fixed ordered root list (bounded glob ~6 ms/run; plugin-manifest `"version"` via `sort -V`; baked-dir fallback; dev-pinned render mode) (see `memory-bank/active/creative/creative-shim-staleness-resolution.md`)
- [x] **Q2 — Shim generation surface & template home** → Resolved: new `stockroom.shim` module CLI as the dispatcher's sixth subcommand; template ships in-package at `src/stockroom/shim_template.sh`; `make shim` delegates; pinned dev variant is a render-time mode, no separate `stockroom-dev` (see `memory-bank/active/creative/creative-shim-generation-surface.md`)

## Status

- [ ] Component analysis complete
- [ ] Open questions resolved
- [ ] Test planning complete (TDD)
- [ ] Implementation plan complete
- [ ] Technology validation complete
- [ ] Preflight
- [ ] Build
- [ ] QA
