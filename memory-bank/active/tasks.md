# Task: p3-m3-sr-initialize-torch-cli

* Task ID: p3-m3-sr-initialize-torch-cli
* Complexity: Level 3
* Type: feature

Milestone m3 of `p3-onboarding-cli-scheduling`: the `sr-initialize` onboarding skill's prerequisites/torch/CLI-binding half — prerequisite checks (uv present and usable), platform/accelerator detection, per-machine out-of-band torch provisioning, a loud-failing smoke test (print version, check `cuda.is_available()`, encode one string), and installation of the m2 shim — validated on the Linux/CUDA path and a CPU path (macOS/MPS reasoning folded into the smoke test). Scheduling and first run are m4; wrapper-skill trimming is m5.

## Component Analysis

### Affected Components

- `skills/sr-initialize/SKILL.md` (new): the operator-invoked onboarding skill. Both manifests already expose the whole `skills/` tree, so a new skill dir ships without manifest changes.
- Engine (`skills/sr-search/src/stockroom/`): some amount of new tested Python (exact surface is the open question) — prerequisite checks, accelerator detection, torch smoke test.
- Dispatcher `stockroom.__main__.SUBCOMMANDS`: new row(s) if a new module lands (auto-sizing `_usage()` verified in m2).
- `stockroom.shim` (m2, unchanged): `sr-initialize` binds the CLI via `stockroom shim install --owner <harness>` — reuse, never reimplement.
- Licensing (`REUSE.toml`): existing annotations already cover a new skill dir (`skills/**` PPL-S; `skills/**/*.py` etc. re-asserted AGPL); verify, don't change.
- Docs: README onboarding touchpoint; `memory-bank/techContext.md` accretes the new surface.

### Cross-Module Dependencies

- `sr-initialize` (prose) → engine invocation **before the shim exists**: the skill is the system's sanctioned bootstrap and must carry the one pre-shim incantation (plugin-root env var + torch-safe uv flags). This is the *only* place outside the shim allowed to know it (litter-audit: understanding lives in the initializer).
- `sr-initialize` → `stockroom shim install`: the CLI-binding step is a call into the m2 module CLI.
- Smoke test → torch at runtime: engine-side tests must follow the `importorskip("torch")` gating convention; CI stays torch-free.
- Torch provisioning → `uv pip install torch --no-config --index <url>` (o9 spike recipe, already wrapped by `make torch` for dev).

### Boundary Changes

- Possible new dispatcher subcommand(s) — additive only; existing module CLIs untouched.
- New skill directory — additive; committed layout = install layout.

### Invariants & Constraints

- Torch-safe contract: torch never in the lock, provisioned out of band, never an exact sync anywhere (`--no-sync` / `--inexact` only).
- Torch wheel choice is a **per-machine human decision** (o9 spike: wrong wheel crashes at kernel launch); detection informs a recommendation, the user confirms.
- Smoke test must fail loudly at setup: print `torch.__version__`, `cuda.is_available()`, and actually encode one string.
- Shim writes only via `stockroom.shim` ownership policy (`install --owner <harness>`).
- All Python test-first; skill prose verified artisanally by the operator.
- No Windows-native path (POSIX only; WSL is the Linux path).

## Open Questions

- [x] **Q1 — Onboarding logic surface (Python/prose split)** → Resolved: read-only `stockroom doctor` module (`probe` torch-free facts + `smoke` loud-failing real-encoder check) as the dispatcher's seventh subcommand, with skill prose owning bootstrap, the human-confirmed wheel choice, provisioning, and shim binding via `stockroom shim install` (see `memory-bank/active/creative/creative-onboarding-logic-surface.md`)
- [x] **Q2 — Accelerator detection & index recommendation** → Collapsed into Q1: `probe` reports mechanical facts (`platform`, `nvidia-smi`, torch import state); the index-recommendation mapping is judgment and lives in skill prose, confirmed by the user

## Status

- [x] Component analysis complete
- [ ] Open questions resolved
- [ ] Test planning complete (TDD)
- [ ] Implementation plan complete
- [ ] Technology validation complete
- [ ] Preflight
- [ ] Build
- [ ] QA
