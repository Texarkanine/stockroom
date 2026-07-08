# Project Brief

## User Story

As the stockroom operator, I want a single `sr-initialize` run to self-configure a machine — torch provisioned and smoke-tested, an on-path `stockroom` command bound, nightly ingest + embed scheduled, and a first full ingest + embed completed — so that the spine's one-command promise is real and every engine invocation (skills, scheduler, and the later dashboard) flows through one drift-safe contract instead of a fragile copy-pasted incantation.

## Use-Case(s)

### Use-Case 1: One-command onboarding on a clean machine

A user installs the plugin and runs `sr-initialize`. It checks prerequisites (uv present and usable), detects platform and accelerator, provisions the per-machine torch wheel via the proven out-of-band recipe, and smoke-tests it (prints version, checks `cuda.is_available()`, encodes one string) — failing loudly at setup on a wrong wheel. It binds `~/.local/bin/stockroom`, installs the nightly scheduler, and performs a first full ingest + embed, leaving a populated, embedded, query-ready warehouse with no manual configuration.

### Use-Case 2: One-word engine invocation everywhere

Any skill, cron entry, hook, or human runs `stockroom <subcommand>` (`query`, `semantic`, `ingest`, `embed`, `migrate`). The shim owns the torch-safe run contract (`--no-sync --no-config`, `PYTHONPATH`, `APP_DIR`) in exactly one generated file, bake-then-verify so a plugin update that moves the cache cannot leave a stale invocation.

### Use-Case 3: Overnight freshness without attention

Cron (Linux) or launchd (macOS) runs `stockroom ingest` and `stockroom embed` nightly, invoking the shim — never a raw engine path — so no rendered-out artifact can bake a stale plugin-cache location.

## Requirements

Phase 3 of `planning/roadmap.md`, three roadmap milestones:

1. **`sr-initialize` — prerequisites, torch, and the on-path CLI**: prerequisite checks, platform/accelerator detection, per-machine torch provisioning, loud-failing torch smoke test; a tested `python -m stockroom` dispatcher over the existing modules; a generated bake-then-verify shim on PATH owning the torch-safe run contract. The plugin-update staleness question (how a baked `APP_DIR` is detected stale and re-resolved) is decided here.
2. **`sr-initialize` — scheduling and first run**: nightly ingest + embed via cron (Linux) or launchd (macOS), entries invoking the shim with correct per-machine resolution; first full ingest + embed leaving a populated, embedded warehouse. Windows-native scheduling stays out of v1.
3. **Wrapper-skill trimming pass**: across `sr-query` / `sr-semantic` / `sr-search`, swap every invocation incantation for `stockroom <subcommand>`, apply the litter-audit inventory (rationale → shared reference doc; task knowledge stays in the skill), add the one shared-doc pointer per skill, re-run the m6 grep-verifiable no-invocation-token check.

## Constraints

1. Test-first (workspace TDD rule) for all Python; prompt-skill behavior verified artisanally by the operator, per project invariant.
2. Torch-safe contract is inviolable: torch out of the lock, provisioned out of band, never an exact sync.
3. Scheduler entries and all rendered-out artifacts invoke the shim — no raw engine paths anywhere.
4. No fallback incantation in skills: `command -v stockroom` fails → tell the user to run `sr-initialize` (per `planning/brainstorm/stockroom-on-path-cli.md`).
5. Open design questions listed in `planning/brainstorm/stockroom-on-path-cli.md` (resolution order across harness caches, shim template location, uv-missing behavior, dev-repo ergonomics, staleness detection) are resolved inside this phase.
6. Committed layout equals install layout; the engine stays run-in-place (`package = false`) — no console-script entry points.

## Acceptance Criteria

From the roadmap's "Done when":

1. A single `sr-initialize` run on a clean machine self-configures nightly freshness and produces a populated, embedded, query-ready warehouse with the torch smoke test green.
2. Validated on at least a Linux/CUDA path and a CPU-or-macOS path (the torch paths the spike only reasoned about get validated on real target machines, folded into the smoke test).
3. The on-path `stockroom` command drives every engine call — skills, scheduler, and (later) the dashboard.
4. The three wrapper skills carry `stockroom <subcommand>` with zero invocation plumbing, grep-verified.
