# Architecture Decision: Shim Generation Surface & Template Home

## Requirements & Constraints

Ranked quality attributes:

1. **Testability** — generation/installation is product logic; the TDD rule binds it. It must be exercisable by pytest without touching the real `~/.local/bin`.
2. **Single ownership** — exactly one implementation of "render + install + verify", drivable by all three consumers: the m3 `sr-initialize` skill, a repo developer (`make shim`), and a human re-running it ad hoc.
3. **Reviewability / licensing** — the template is a shipped, REUSE-covered artifact, not a heredoc buried in Python or skill prose.
4. **Packaging honesty** — run-in-place (`package = false`); no console-script entry points; committed layout = install layout.

Scope boundary: *what renders and installs the shim, and where the template lives*. The shim's internal selection algorithm is decided in `creative-shim-staleness-resolution.md`.

## Components

- **Template** (`stockroom-shim.sh` + a dev-pinned mode): POSIX sh with a small set of render-time substitutions (baked `APP_DIR`, mode, version stamp).
- **Generator** (tested Python): renders the template, writes the executable atomically, idempotent on re-run, checks PATH membership, runs the install-time `stockroom --version` verify.
- **Consumers**: m3 `sr-initialize` (drives onboarding), `make shim` (dev parity), the dispatcher's own `--help` (discoverability).

## Options Evaluated

Two nearly-independent axes, evaluated together because the natural pairings differ:

- **Surface S1 — dispatcher subcommand `stockroom shim`**: a new `stockroom.shim` module CLI, one more row in the `SUBCOMMANDS` table.
- **Surface S2 — library-only helper**: `stockroom.shim.install()` with no CLI; m3 and `make shim` each craft their own invocation (`python -c …` or a bespoke script).
- **Template home T1 — inside the package** (`src/stockroom/shim_template.sh`): loaded `Path(__file__)`-relative by the generator.
- **Template home T2 — engine-adjacent scripts dir** (`skills/sr-search/scripts/stockroom-shim.sh`): the brainstorm's sketch; generator reaches out of `src/` to find it.

## Analysis

**Surface.** S1 wins on every ranked attribute. The engine already has exactly one pattern for "tested operational verb": a module with `main(argv) -> int` behind the dispatcher — the m1 reflection explicitly advises preserving that shape for future verbs. A subcommand gives all three consumers the *same* entrypoint: m3 runs the raw incantation once (`PYTHONPATH=… uv run … python -m stockroom shim`) and everything after that is `stockroom <sub>`; `make shim` is a one-line delegation; `stockroom --help` advertises it. S2 forces each consumer to reinvent an invocation (exactly the incantation-litter this phase exists to kill) and leaves the verb undiscoverable. S1's only cost is a sixth `SUBCOMMANDS` row.

There is a pleasing structural consequence: `stockroom shim` regenerates the shim *through the current engine*, so post-update healing has a tested Python home (`stockroom shim` re-bakes) while the sh-level selection logic stays a thin safety net.

**Template home.** T1 keeps the template inside the only directory the generator can locate unconditionally (`Path(__file__).parent`) — under `package = false` run-in-place there is no wheel/data-files indirection to worry about, and the committed file *is* the installed file. T2 buys nothing (reviewability is identical — both are committed files) and costs a fragile `../..`-style escape from `src/` plus a second top-level location to keep REUSE-annotated. The brainstorm's actual requirement was "reviewable and REUSE-covered rather than a heredoc" — T1 satisfies it.

Key insights:

- The dev-parity question collapses into a render-time flag, not a second artifact: `stockroom shim --app-dir <checkout>/skills/sr-search` generates the *pinned* variant (no re-resolution — see the staleness decision's dev-pinned mode). `make shim` passes the checkout path. The brainstorm's speculative separate `stockroom-dev` shim is rejected (YAGNI): one shim, one PATH name, mode chosen at render time; re-running `sr-initialize` or `make shim` flips it. A `--dest` flag (default `~/.local/bin/stockroom`) is what makes the generator testable against a tmp dir.
- REUSE ripple: `REUSE.toml`'s code-shaped re-assert list does not currently match `*.sh` under `skills/**`, so the template would resolve PPL-S. Add `skills/**/*.sh` to annotation block 3 — shell is software, not prompt content.
- The `Makefile` must invoke `make shim` via its existing `UV_RUN` contract plus `PYTHONPATH=$(ENGINE)/src` (the run-in-place import rule that pytest alone escapes).

## Decision

**Selected**: S1 + T1 — a `stockroom.shim` module CLI registered as the dispatcher's sixth subcommand, with the template shipped inside the package at `src/stockroom/shim_template.sh`.

**Rationale**: reuses the engine's one established verb pattern (testability and discoverability for free), gives every consumer the same single entrypoint (single ownership), and keeps the template in the one location that is unconditionally locatable and already committed-equals-installed (packaging honesty). The template stays a reviewable, REUSE-covered file.

**Tradeoff**: the shim verb ships to end users who will rarely invoke it directly (m3 drives it during onboarding) — accepted for the self-healing "re-run `stockroom shim`" story and dev parity.

## Implementation Notes

> **Revised 2026-07-08** after the operator superseded the Q1 staleness decision (see `creative-shim-staleness-resolution.md`): the shim is baked-only (no pinned/normal mode split — every shim is "pinned"), ownership is explicit, and healing moves to a sessionStart hook. The surface decision (S1 + T1) stands unchanged; the notes below reflect the revised shape.

- New module `stockroom.shim`: `render(app_dir, owner) -> str`, `install(dest, app_dir, owner, *, takeover=False) -> report`, `rectify(dest, app_dir, owner) -> report`, `main(argv) -> int` with subactions `install` / `rectify`, `--app-dir` (default: auto-resolve own engine dir from `stockroom.__file__`), `--dest` (default `~/.local/bin/stockroom`), `--owner`, `--takeover`. Ownership/takeover/no-op policy per the Q1 decision — all in tested Python.
- Dispatcher: add `"shim"` row to `SUBCOMMANDS` (lazy import as with the rest).
- Install semantics: write mode `0o755`, atomic replace (temp file + `os.replace`) for idempotent re-runs; report PATH membership of the dest dir (warn, don't fail); then the `--version` verify through PATH when the dest dir is on PATH.
- Hook wiring (new artifacts): dual hook configs (Cursor and Claude schemas differ) each invoking `… python -m stockroom shim rectify --owner <harness> --app-dir ${<HARNESS>_PLUGIN_ROOT}/skills/sr-search`, silenced and non-blocking; manifest pointers added (`.cursor-plugin/plugin.json` `"hooks"` key; Claude default `hooks/hooks.json`).
- `Makefile`: `shim:` target delegating to the dispatcher with the checkout's engine dir and `--owner dev`.
- `REUSE.toml`: extend code-shaped override with `skills/**/*.sh`.
- README: ad-hoc-invocation section rewritten around the installed `stockroom <subcommand>` with `stockroom shim install` (or `make shim`) as the way to get it.
