# Progress

Milestone m3 of L4 project `p3-onboarding-cli-scheduling`: build the `sr-initialize` onboarding skill's prerequisites/torch/CLI-binding half — prerequisite checks (uv present and usable), platform/accelerator detection, per-machine out-of-band torch provisioning, a loud-failing smoke test (print version, check `cuda.is_available()`, encode one string), and installation of the m2 shim — validated on the Linux/CUDA path and a CPU path (macOS/MPS reasoning folded into the smoke test). See `memory-bank/active/milestones.md` (m3) and `memory-bank/active/projectbrief.md`.

**Complexity:** Level 3

## 2026-07-08 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - `/niko` re-entry routed the L4 project through milestone advancement: m2 checked off, m2 sub-run ephemeral state deleted
    - m3 classified as Level 3: complete feature across multiple components (orchestrating prompt skill, prerequisite checks, platform/accelerator detection, torch provisioning, smoke test, shim binding) without system-wide architectural implications
    - Fresh sub-run ephemeral state written: `progress.md`, `activeContext.md`, stubbed `tasks.md`; `projectbrief.md` and `milestones.md` preserved
* Decisions made
    - Level 3 classification, matching the milestone's estimate — the split between tested Python helpers and skill prose is a design decision reserved to this run, justifying a creative phase
* Insights
    - m2 delivered the shim install path as a tested module CLI (`stockroom shim install`) — m3's CLI-binding step should invoke it, not reimplement it
    - The torch-safe contract (out-of-band provisioning, never an exact sync) is a cross-milestone invariant; the provisioning recipe was proven in an earlier spike and this milestone productizes it

## 2026-07-08 - CREATIVE - COMPLETE

* Work completed
    - One open question explored and resolved with high confidence: `creative-onboarding-logic-surface.md` (architecture)
    - Per the m2 reflection's process insight, the exploration led with the never-do list (never exact-sync after torch, never pick the wheel silently, never report broken as success, never bypass shim ownership, never plant a second incantation garden) before ranking candidates
* Decisions made
    - Q1: read-only `stockroom doctor` module — `probe` (torch-free environment facts: OS/arch/GPU/driver/torch state) + `smoke` (loud-failing: version, `cuda.is_available()`, one real `BgeEncoder` encode) — as the dispatcher's seventh subcommand; skill prose owns bootstrap (the one pre-shim incantation), the human-confirmed wheel choice, the documented `uv pip install torch --no-config --index` line, and shim binding via `stockroom shim install --owner <harness>`
    - Q2 collapsed into Q1: `probe` reports facts only; the index-recommendation mapping is judgment in skill prose, confirmed by the user
    - Monolithic `stockroom init` rejected (the human wheel confirmation forces a two-phase CLI anyway); prose-only rejected (puts the load-bearing smoke logic in the untestable layer)
* Insights
    - The bootstrap boundary is irreducible: the uv check, engine-dir resolution, and initial exact sync cannot be engine Python because the engine only runs through uv — accepting that dissolves the Python/prose tension
    - This is the established judgment-vs-mechanism split (engine superpowers / wrapper skills) applied to onboarding, not a new pattern
    - The initial `uv sync --frozen --no-config` is the one legitimate exact sync (torch does not exist yet); ordering is load-bearing and the skill must state it
