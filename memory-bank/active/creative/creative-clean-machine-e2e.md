# Decision: Clean-Machine E2E Methodology

## Context

**What**: Choose the environment and isolation strategy that counts as a valid Phase-5 "clean machine" proof of marketplace install → `sr-initialize` → all four surfaces against real Cursor and Claude Code history.

**Why it matters**: Every build step (what to wipe, where the plugin comes from, what the agent vs operator does, what evidence to keep) hangs on this. The wrong bar either (a) claims "clean" while still using a local checkout / polluted warehouse, or (b) demands a second physical machine that blocks shipping without improving the product claim.

**Constraints**:
- Both harnesses (Cursor and Claude Code)
- Real Cursor + Claude history (not synthetic fixtures as the primary claim)
- Engine only via on-path `stockroom` / `sr-initialize` (no raw `uv`/`PYTHONPATH`/`APP_DIR` in the proof narrative)
- Marketplace path is the primary install claim (local `--plugin-dir` / `~/.cursor/plugins/local/` are not the success story)
- Versioning already proven by live release-please cuts (v0.1.0 / v0.1.1 lockstep into both plugin manifests) — do not re-cut a release solely for this milestone
- Marketplace catalog entries are merged (`txrk9-agent-plugins` PR #2)
- L4 invariants: dual-manifest no-build, no marketplace version pin, both harnesses always

## Options Evaluated

- **A — Literal second machine / VM**: Provision a fresh OS (or VM) with Cursor + Claude Code, add marketplace, install, initialize, prove surfaces there.
- **B — Same-host isolated warehouse + marketplace reinstall**: On this WSL host, point `STOCKROOM_HOME` at a fresh directory, remove any local/dev plugin load, install stockroom from the marketplace in both harnesses, run the spine, capture evidence.
- **C — Operator runbook only (no isolation contract)**: Agent writes a checklist; operator runs it somehow; no prescribed `STOCKROOM_HOME` / uninstall steps.

## Analysis

| Criterion | A — Second machine | B — Same-host isolation | C — Runbook only |
|-----------|--------------------|-------------------------|------------------|
| Fidelity to "fresh user" | Highest | High if marketplace install + empty `STOCKROOM_HOME` | Low / undefined |
| Real harness history available | Must copy or recreate | Already present | Depends |
| Agent automatable | Low (UI + new box) | Medium (CLI/verify); UI still human | Low |
| Cost / time | High | Low | Low |
| Risk of false "clean" | Low | Medium if local plugin left loaded | High |
| Reversibility | N/A | High (`STOCKROOM_HOME` throwaway) | N/A |

Key insights:
- Marketplace add/install in Cursor and Claude Code is **UI-bound** — the agent cannot honestly own those clicks. Any winning option is operator-driven for the install half.
- `STOCKROOM_HOME` is a first-class override in tech context; an empty home is a legitimate clean warehouse without destroying the operator's real data.
- Release-please half of m3 is **already satisfied** by merged release PRs #10 / #11 (both manifests + `.release-please-manifest.json` at `0.1.1`). The remaining work is the E2E spine proof, not another version bump.
- Option C fails the milestone's "clean machine" language by omitting an isolation contract. Option A is valid but disproportionate once B's isolation is honest.

## Decision

**Selected**: **B — Same-host isolated warehouse + marketplace reinstall**, executed as an **operator-driven runbook** with agent-prepared steps and agent-verified CLI outcomes.

**Rationale**: Satisfies "clean" (empty `STOCKROOM_HOME`, marketplace-sourced plugin, no local/dev loader) and "real data" (this host's Cursor/Claude history) without requiring a second machine. Matches how the product is actually configured (`STOCKROOM_HOME` / XDG). Acknowledges the hard UI boundary: operator performs marketplace install; agent prepares the runbook, verifies release evidence, and checks post-install CLI/skill outcomes.

**Tradeoff**: Not a literal virgin OS image. Accepted because the product claim is about install path + empty warehouse + real harness roots — not about proving Cursor/Claude themselves install on bare metal.

## Implementation Notes

- **Release half (verify, don't re-cut)**: Record evidence that release-please synced `$.version` into both plugin manifests (PRs #10/#11, tags `v0.1.0`/`v0.1.1`, current lockstep `0.1.1`). Packaging unit tests already cover config/extra-files; no new release required unless lockstep is broken.
- **E2E runbook artifact**: Add a short operator checklist under `memory-bank/active/` during build (or a durable note in reflection/archive evidence) covering: unset local plugin loads → add `https://github.com/Texarkanine/txrk9-agent-plugins` → install stockroom in both harnesses → export fresh `STOCKROOM_HOME` → `/sr-initialize` (Cursor) and `/stockroom:sr-initialize` (Claude) → prove four surfaces → capture command output / URLs.
- **Agent role**: Prepare runbook; verify release evidence; after operator install, run/observe `stockroom doctor`, warehouse queries, and surface smoke checks under the isolated home; update roadmap Phase 5 checkboxes when proof lands.
- **Do not**: Treat `claude --plugin-dir` or `~/.cursor/plugins/local/` as the primary success path; invent CI for marketplace UI; pin marketplace manifests to a stockroom version.
