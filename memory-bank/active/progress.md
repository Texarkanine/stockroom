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

## 2026-07-08 - PLAN - COMPLETE

* Work completed
    - Component analysis: `stockroom.doctor` (new read-only module, probe + smoke), dispatcher seventh `SUBCOMMANDS` row, `skills/sr-initialize/SKILL.md` (new prose skill), README/techContext/systemPatterns accretion; `stockroom.shim` and `BgeEncoder` reused unchanged; REUSE globs already cover the new paths
    - Test plan: 16 behaviors — probe facts/graceful-degradation (B1–B7), smoke loud-failure shapes incl. wrong-width vectors (B8–B11), one `importorskip("torch")` real-model smoke (B12), CLI + dispatcher integration (B13–B16); new `test_doctor.py` / `test_doctor_cli.py`, extended `test_dispatcher_cli.py`
    - Six-step ordered plan in `tasks.md`: probe → smoke → CLI/dispatcher (each red→green) → SKILL.md prose → docs → live validation (Linux/CUDA + CPU via `CUDA_VISIBLE_DEVICES=""`) + `make ci`
* Decisions made
    - The torch-absent smoke diagnosis (exit 1, one stderr line) is CI-testable torch-free by construction — the loud-failure contract does not hide behind the torch skip
    - `nvidia-smi` probed via `--query-gpu=` CSV mode; every subprocess failure is a reportable fact, never an error
    - Full-flow onboarding verification is live/artisanal (prose orchestration over tested units), not pytest — consistent with the project invariant
* Insights
    - The m2 acceptance-spine analogue for m3 is B10: a wrong-width vector must fail the smoke — "encodes but corrupts" is the subtlest wrong-wheel failure mode
    - m4 will reuse `doctor probe`/`doctor smoke` to validate the environment before installing scheduler entries

## 2026-07-08 - PREFLIGHT - COMPLETE (PASS)

* Work completed
    - TDD encoding, convention compliance, dependency impact, conflict detection, and completeness verified against the codebase; `.preflight-status` written PASS
    - Verified: `doctor` name is unclaimed; `SUBCOMMANDS` is consumed only by `__main__` and `test_dispatcher_cli.py` (the `.cursor/skills/stockroom-local` hits are the localdev symlink mirror); `test_packaging.py` does not enumerate skill dirs so `skills/sr-initialize/` lands free; REUSE.toml globs (`skills/**` PPL-S, `skills/**/*.py` AGPL re-assert) cover every new path with no annotation change; importing `stockroom.embed` for `BgeEncoder` is torch-free (lazy torch import inside the constructor, documented + relied on by existing CI)
    - One plan amendment (fixable in place): README line ~78 enumerates the dispatcher subcommands — step 5 now includes adding `doctor` to that list
* Decisions made
    - No blocking findings; one advisory recorded (a `shim`-status fact in `doctor probe` was considered for re-run idempotency and rejected — `command -v stockroom` in skill prose is simpler; revisit only if m4 needs it)
* Insights
    - `test_dispatcher_cli.py`'s fingerprint table makes the seventh-row extension mechanical: add `doctor` to the tuple and `"probe"` as its fingerprint

## 2026-07-08 - PLAN (AMENDED AT GATE) - COMPLETE

* Work completed
    - Operator review at the preflight→build gate raised four points; all answered and folded into `tasks.md` (no component/dependency changes — preflight PASS stands)
    - Confirmed the operator's user-level `~/.config/uv/uv.toml` (pytorch-cu126 index) is unnecessary and unread under the planned path: provisioning carries the index explicitly with `--no-config`, and that config file is the canonical instance of the ambient state the o9 spike's hermetic rules defend against
* Decisions made
    - **Errmsg ratchet is now a stated invariant**: every init-path failure carries the next action; `doctor` prints exact commands (it knows `APP_DIR`); B8/B9/B10/B14 assert remedy content, not just failure — torch-missing must name the engine environment (the "I have torch globally" trap)
    - **Self-managed-torch branch added to the skill**: state the requirement (torch importable in the engine env, any build that passes smoke), let the user install their way; the smoke test is the gate, not the recipe
    - **Idempotent re-entry stated**: no progress file — the environment is the state; re-running `sr-initialize` re-probes and skips green steps, making "come back once you did that" a supported flow
    - **Engine resolution falls back sibling-relative** (`../sr-search` from the skill's own dir, the `sr-search` precedent) so `make localdev` trials work without `*_PLUGIN_ROOT`; unset plugin roots signal dev context (shim defers to `make shim`; a harness-owner install against the live dev shim is a correctly-relayed ownership refusal)
* Insights
    - The probe/smoke split absorbed every operator scenario without structural change — verification-as-the-gate is what makes provisioning method-agnostic

## 2026-07-08 - BUILD - COMPLETE

* Work completed
    - `stockroom.doctor` landed TDD red→green: `probe` (torch-free facts incl. `gpu-compute-cap` + `driver-cuda`, every nvidia-smi failure a reported fact) and `run_smoke` (ratcheted one-line failures through the real `BgeEncoder`); flat `probe|smoke` CLI; dispatcher's seventh `SUBCOMMANDS` row — 19 new tests (`test_doctor.py`, `test_doctor_cli.py`) + `test_dispatcher_cli.py` extension, all 16 behaviors covered
    - `skills/sr-initialize/SKILL.md` written with every example executed live first: sibling-relative engine resolution, the guarded one-legitimate-exact-sync, probe → human-confirmed wheel → out-of-band cu126 install → smoke, self-managed-torch branch, shim binding with refusal/PATH relay, idempotent re-entry semantics
    - Docs accreted (README subcommand list + onboarding pointer; techContext doctor/sr-initialize sections; systemPatterns onboarding split note); `make localdev` mirror refreshed to include `sr-initialize`
    - Live validation on this machine: CUDA path (smoke exit 0, cuda True, B12 un-skipped), CPU path (`CUDA_VISIBLE_DEVICES=""` smoke exit 0), ownership-refusal relay, idempotent re-install, and the sync-strips-torch hazard all observed; `make ci` green (pytest, ruff, lock-check, REUSE)
* Decisions made
    - Smoke's torch-missing remedy prints `uv pip install … --directory <engine>` (not `--project`): `uv pip --project` fails without a cwd venv — verified live, asserted in B8
    - B14 self-skips when torch is importable, making it the exact complement of the `importorskip` real-model smoke (each environment runs one of the pair)
* Insights
    - Live-verifying examples before writing them into prose caught two real bugs the unit suite could not: the `--project` remedy that would have been a dead command, and `make shim` baking relative paths into a dead shim (`uv --directory` moves the cwd)

## 2026-07-08 - QA - COMPLETE (PASS)

* Work completed
    - Semantic review of the full build against the plan and creative decision: KISS/DRY (flat module mirroring `stockroom.shim`, no new abstraction layers), YAGNI (rejected advisories stayed rejected — no `--json`, no shim-status fact), completeness (all 16 behaviors implemented and asserted; every plan-step-4 SKILL.md item present), regression (dispatcher/test/licensing conventions all followed; REUSE 194/194), integrity (no debug artifacts or placeholders), documentation (README/techContext/systemPatterns updated with the change)
    - `.qa-validation-status` written PASS; no fixes required
* Decisions made
    - New techContext/systemPatterns sections keep those files' existing hard-wrapped paragraph style (consistency with surrounding content over the no-hard-wrap preference) — recorded, not changed
* Insights
    - The B14/B12 complement (subprocess torch-free smoke self-skips when torch is importable; the real-model test skips when it is not) means every environment runs exactly one of the pair — the loud-failure contract is never untested anywhere
