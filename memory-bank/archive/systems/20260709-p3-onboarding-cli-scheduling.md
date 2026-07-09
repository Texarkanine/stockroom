---
task_id: p3-onboarding-cli-scheduling
complexity_level: 4
date: 2026-07-09
status: completed
---

# TASK ARCHIVE: Phase 3 — Onboarding, On-Path CLI, and Scheduling

## SUMMARY

Phase 3 made stockroom's "one-command" promise real. A single `sr-initialize` run now self-configures a machine end to end: it checks prerequisites, detects platform and accelerator, provisions and smoke-tests a per-machine torch wheel, binds an on-path `stockroom` command, installs a nightly ingest + embed schedule, and performs a first full ingest + embed — leaving a populated, embedded, query-ready warehouse with no manual configuration.

The architectural spine of the phase is the **torch-safe invocation contract owned in exactly one place**. Every engine call — skills, scheduler, and human — now flows through a generated `~/.local/bin/stockroom` shim that bakes the run contract (`--no-sync --no-config`, `PYTHONPATH`, `APP_DIR`) and self-heals when a plugin update moves the cache. Behind the shim sits a tested `python -m stockroom` dispatcher over the existing module CLIs. The phase closed by trimming the three wrapper skills down to `stockroom <subcommand>` with zero invocation plumbing, moving the rationale into one shared reference doc, and pinning the no-incantation invariant as a permanent CI test.

Delivered as a Level 4 project across five sequential milestones (m1→m5), each an independent sub-run (two L2, three L3). Every milestone landed to plan with a clean or near-clean QA.

## REQUIREMENTS

From `projectbrief.md` (Phase 3 of `planning/roadmap.md`):

1. **`sr-initialize` — prerequisites, torch, and the on-path CLI**: prerequisite checks, platform/accelerator detection, per-machine torch provisioning, loud-failing smoke test; a tested `python -m stockroom` dispatcher; a generated bake-then-verify shim on PATH owning the torch-safe run contract. Resolve the plugin-update staleness question in-phase.
2. **`sr-initialize` — scheduling and first run**: nightly ingest + embed via cron (Linux) or launchd (macOS) invoking the shim with correct per-machine resolution; first full ingest + embed leaving a populated, embedded warehouse. Windows-native scheduling out of v1.
3. **Wrapper-skill trimming pass**: swap every invocation incantation for `stockroom <subcommand>` across `sr-query` / `sr-semantic` / `sr-search`, apply the litter-audit inventory (rationale → shared reference doc; task knowledge stays in the skill), add one shared-doc pointer per skill, re-run the grep-verifiable no-invocation-token check.

### Cross-milestone invariants (held throughout)

- **Torch-safe contract inviolable**: torch out of the lock, provisioned out of band, no exact sync anywhere (`--no-sync` / `--inexact` only).
- **No raw engine paths in any rendered-out artifact**: everything outside the repo invokes `stockroom <subcommand>` (the self-healing shim is the sole owner of the baked path).
- **The shim does environment plumbing only; the dispatcher owns all logic.** Shim stays too dumb to need tests.
- **No fallback incantation in skills**: `command -v stockroom` failing means "run `sr-initialize`".
- **Run-in-place packaging holds**: `[tool.uv] package = false`, committed layout = install layout, no console-script entry points.
- **Test-first for all Python; prompt skills verified artisanally** — every shipped SKILL.md example executed live before write-in; green `make ci` (incl. REUSE) at every milestone boundary.
- **Windows-native scheduling out of v1** (POSIX cron/launchd only; WSL is the Linux path).
- **Existing read/write chokepoints untouched**: all engine surfaces keep going through `warehouse.open()`; the dispatcher wraps module CLIs, it does not reimplement them.

## IMPLEMENTATION

### Milestone list (as planned, as executed)

The five milestones executed in the planned serial order with **no additions, removals, re-scoping, or reordering** at the project level. Estimated levels held exactly (m1 L2, m2 L3, m3 L3, m4 L3, m5 L2). The dependency graph (`m1→m2→m3→{m4, m5}`) was realized as a valid serial run.

- [x] **m1 — `stockroom` dispatcher (L2)**
- [x] **m2 — bake-then-verify `stockroom` shim (L3)**
- [x] **m3 — `sr-initialize`: prerequisites, torch, and CLI binding (L3)**
- [x] **m4 — `sr-initialize`: scheduling and first run (L3)**
- [x] **m5 — wrapper-skill trimming pass (L2)**

### Key artifacts created

- `src/stockroom/__main__.py` — the `python -m stockroom` dispatcher; a uniform `SUBCOMMANDS` table forwarding first-token dispatch to each module's `main(argv)`.
- `src/stockroom/migrate.py` CLI entrypoint — authored to fill the previously library-only gap.
- `src/stockroom/shim.py` — tested Python that renders/installs the POSIX-sh shim from a REUSE-covered template; the dispatcher's sixth subcommand.
- `src/stockroom/doctor.py` — read-only `probe` (torch-free facts) + `smoke` (loud-failing real-encoder path); the seventh subcommand.
- `src/stockroom/schedule.py` — `install | status | remove` over cron and launchd with a shared payload renderer; the eighth subcommand.
- `skills/sr-initialize/SKILL.md` — the orchestrating onboarding prose skill (prereqs → torch → smoke → shim → schedule → first run).
- `skills/sr-search/references/system-model.md` — the shared *why* reference doc.
- `skills/sr-search/tests/test_skill_hygiene.py` — the permanent no-invocation-token pytest.

### Design decisions of record

- **Staleness healing (the plugin-update TODO)**: resolved as **baked-only + hook rectification + ownership marker**, *not* runtime scan-and-rank. An always-scan/version-ranked design was vetoed at the m2 preflight→build gate against the hard "never guess" constraint; the replacement moved all policy into tested Python and left the sh template with three checks and an exec.
- **Doctor split**: read-only `probe`/`smoke` in Python (facts), orchestration judgment in prose (choices) — the facts/judgment boundary drove the whole m3 shape.
- **Scheduling**: flat `stockroom.schedule`, a managed crontab block / owned plist, a shared payload renderer, judgment (consent, time-of-night) in prose; foreign crontab lines preserved byte-for-byte under test.
- **Skill trimming**: driven by the pre-existing `planning/brainstorm/skill-litter-audit.md` (Categories A–C removed, D kept as a literal keep-list); rationale relocated to one shared doc with one pointer per skill.

## TESTING

Every milestone was gated by `make ci` (pytest + ruff lint/format + lock check + REUSE compliance), and every milestone used the project's TDD discipline (tests red-first) for all Python plus artisanal live verification for all prose.

- **m1**: 11 subprocess tests, red-first, all green on first implementation; QA caught two doc gaps (fixed in QA).
- **m2**: all 8 steps red→green; the "exactly one stderr line" assertion caught a backtick command-substitution injection in rendered text; one trivial KISS QA fix.
- **m3**: three clean red→green cycles; validated live on **both** the Linux/CUDA and CPU paths; live verification caught two environmental bugs (`uv pip --project` vs `--directory`; `make shim` baking relative paths) that no unit seam could reach.
- **m4**: 17 behaviors test-pinned; live crontab validation (backup + foreign-line diff after each mutate) caught a redirection-binding bug in the payload; closed with a real first run — **809 sessions, 29 080 messages, 39 805 vectors**, nightly cron firing at 03:30. Post-milestone operator verification: WSL cron fired overnight; M4 launchd passes on-demand (timer-fire judged sufficient by identical payload/mechanism).
- **m5**: `make ci` green (365 passed, 3 torch-gated skips; REUSE 200/200); the hygiene test written red against the untrimmed skills and driven green by the edits; every shipped example live-executed through the real shim against the real warehouse before write-in.

## SYSTEM STATE

What exists now that didn't before:

- **An on-path `stockroom` command** on the operator's machine(s), owning the torch-safe run contract in one generated, self-healing file. Every engine call — skills, cron, human — routes through it. Raw engine-path invocations no longer appear in any rendered-out artifact.
- **A dispatcher** (`python -m stockroom`) with eight subcommands: `query`, `semantic`, `ingest`, `embed`, `migrate`, `shim`, `doctor`, `schedule`. Each is a thin forward to a module `main(argv)`; `migrate` gained its first CLI this phase.
- **A one-command onboarding skill** (`sr-initialize`) that self-configures a clean machine: prereqs → accelerator detection → out-of-band torch → loud smoke test → shim bind → nightly schedule → first ingest + embed.
- **A live nightly pipeline**: cron on the Linux/WSL box (03:30) and launchd on the M4 MacBook Pro, both invoking the shim by name, both idempotent on re-install.
- **A populated, embedded, query-ready warehouse** (the m4 first run) backing real semantic/keyword search.
- **Three trimmed wrapper skills** carrying `stockroom <subcommand>` with zero invocation plumbing (grep-verified, and now regression-pinned by `test_skill_hygiene.py`), with system-model rationale consolidated into one shared reference doc.

End-to-end, the phase converted a fragile copy-pasted incantation spread across skills, scheduler, and docs into a single drift-safe contract with exactly one owner.

### Acceptance criteria — met

1. Single `sr-initialize` run self-configures nightly freshness and produces a populated, embedded, query-ready warehouse with the torch smoke test green. ✔
2. Validated on a Linux/CUDA path and a CPU-or-macOS path. ✔
3. The on-path `stockroom` command drives every engine call. ✔
4. The three wrapper skills carry `stockroom <subcommand>` with zero invocation plumbing, grep-verified. ✔

## LESSONS LEARNED

- **Move complexity out of the untestable layer.** The single largest risk reduction of the phase (m2) came from relocating staleness policy from the sh template into tested Python — a design *goal*, not a preference, that converts build risk into ordinary TDD work.
- **Live-verifying prose examples is an integration test layer, not a formality.** It caught four real bugs across m3 and m4 (two dead commands, a dead dev shim, a redirection-binding defect) — every one of them outside any injectable unit seam.
- **Pin the exact generated string, not fragments.** Substring assertions are exactly where a semantically-wrong render still passes; m4's redirection bug survived fragment assertions and was only caught live, after which B1 was tightened to pin the whole payload.
- **Error messages are rendered-out surfaces too.** A stderr hint naming a raw module invocation is the same drift class the phase exists to remove; when a contract changes shape, grep the error strings, not just the docs.
- **TDD generalizes to prose when the assertion is mechanical.** A forbidden-token scan written red before editing gave markdown the same red→green discipline as code and survives as a permanent regression pin.

## PROCESS IMPROVEMENTS

- **Surface "never do" constraints before optimizing among algorithms.** m2's veto cost a full plan+preflight rework that one creative-phase question ("what must this component *never* do?") would have avoided. For decisions with a security/trust flavor, ask the prohibition question first.
- **A categorized audit with an explicit keep-list turns a judgment-heavy pass into a mechanical one.** Writing `skill-litter-audit.md` *before* m5 ran was effectively a pre-paid creative phase — it is what kept m5 at L2 and turned QA's "did we over-trim?" into a diff check.
- **The torch-strip interaction is per-invocation, not per-session.** Any dev workflow interleaving `make ci`/`make test`/`make sync` with a torch-dependent run must re-provision torch (`make torch`) in between. Sequencing live examples before the final CI gate makes it a non-event. (The nightly job is immune because the shim runs `--no-sync` — a standing confirmation the contract lives in the right place.)

## TECHNICAL IMPROVEMENTS

- **Module `prog` cosmetics.** Module CLIs still carry `prog="python -m stockroom.<mod>"`, so forwarded `--help` shows module-form usage. Harmless; if the shim's naming story ever wants it, drop the per-module `__main__` guards and let the dispatcher own all program naming (the uniform `main(argv)` shape makes this cheap).
- **`uv pip` vs `uv run` project resolution.** `uv run --project X` works from anywhere, but `uv pip install --project X` needs the venv discoverable from cwd — use `--directory X` for pip operations, and pre-absolutize every path handed through `uv --directory` (it moves cwd before argv is interpreted).

## NEXT STEPS

None required — Phase 3 is complete and its acceptance criteria are met. The natural continuation is the later dashboard work already anticipated in the brief (it will consume the same on-path `stockroom` contract). The **Million-Dollar Question** across sub-runs (m1 and m5 both reached it independently): had the on-path CLI been a foundational Phase-0 assumption, the per-module `__main__` guards, the flag rationale in skills, and the intermediate drift the shim was built to end would never have existed — the system converges exactly on that end-state, and the only cost of arriving late was the drift itself. Worth carrying into any future greenfield spine as a "build the invocation contract first" principle.
