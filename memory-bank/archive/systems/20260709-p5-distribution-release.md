---
task_id: p5-distribution-release
complexity_level: 4
date: 2026-07-09
status: completed
---

# TASK ARCHIVE: Phase 5 — Distribution and Release

## SUMMARY

Phase 5 closed the v1 "clean enough to ship" gate. A fresh user can add the `txrk9-agent-plugins` marketplace, install stockroom on Cursor and Claude Code, run `sr-initialize`, and use all four surfaces (`sr-search` / `sr-semantic` / `sr-query` / `sr-dashboard`) against real harness history. Install/usage docs, dual marketplace catalog entries, a exercised release-please lockstep cut (v0.1.0 → v0.1.1), and a same-host marketplace E2E proof together demonstrate the spine end to end.

Delivered as a Level 4 project across three sequential milestones (m1 L2 → m2 L2 → m3 L3). Estimated levels held. No milestones were added, removed, re-scoped, or reordered. Mid-build course corrections stayed inside milestone scope: m1 dropped CI prose pins and deferred live install proof; m3 left Cursor `sessionStart` auto-dashboard as open [#12](https://github.com/Texarkanine/stockroom/issues/12) rather than expanding the build.

## REQUIREMENTS

From `projectbrief.md` (Phase 5 of `planning/roadmap.md`):

1. **Plugin definition + install docs** — user-facing install/usage documentation (marketplace path + local/dev loaders); per-harness skill-invocation forms (`/sr-*` vs Claude `/stockroom:<skill>`). Live marketplace install and empirical invocation proof deferred to m2/m3. Manifests already existed from Phase 0.
2. **Marketplace entry** — stockroom in both `.cursor-plugin/marketplace.json` and `.claude-plugin/marketplace.json` in `Texarkanine/txrk9-agent-plugins`, pointing at `Texarkanine/stockroom` (follow `slobac` / `cursor-warehouse` shape; no version pin).
3. **Release flow + end-to-end install test** — exercise release-please so version syncs into both stockroom plugin manifests; then prove marketplace add → install → `sr-initialize` → four surfaces on a clean-machine (same-host) path against real Cursor and Claude history.

### Cross-milestone invariants (held throughout)

- **Dual-manifest, no-build template** — committed layout = install layout; no milestone invented a build/bundle step.
- **Versioning stays in stockroom** — release-please syncs `$.version` into both *plugin* manifests only; marketplace manifests never carry a stockroom version pin.
- **Engine invocation stays on-path** — skills/docs/E2E invoke `stockroom <subcommand>` (or `sr-initialize` for first-time setup); no raw `uv`/`PYTHONPATH`/`APP_DIR` in user-facing surfaces.
- **Both harnesses, always** — docs, marketplace entries, and E2E cover Cursor and Claude Code.
- **slobac + official docs are the correctness bar** — packaging and marketplace shape follow `../slobac` and Cursor / Claude Code plugin references.
- **Marketplace is a separate repo** — entries land in `Texarkanine/txrk9-agent-plugins`; stockroom does not host a marketplace.json.

## IMPLEMENTATION

### Milestone list (as planned, as executed)

The three milestones executed in the planned serial order with **no additions, removals, re-scoping, or reordering** at the project level. Estimated levels held (m1 L2, m2 L2, m3 L3).

- [x] **m1 — Install/usage docs + deferred install proof (L2)**
- [x] **m2 — Marketplace entries in txrk9-agent-plugins (L2)**
- [x] **m3 — Release-please exercise + clean-machine E2E spine (L3)**

### Sub-run summaries

#### m1 — Install/usage docs + deferred install proof (L2)

Shipped best-effort README install/usage docs covering the intended marketplace-add path, Cursor/Claude local/dev loaders, and a skill-invocation table (`/sr-*` vs `/stockroom:<skill>`). Removed docstring/prose packaging pins so docs can move without CI fights. Live marketplace install and empirical invocation proof were deliberately deferred until catalog entry (m2) and `main` / clean-machine proof (m3).

Key decisions: treat marketplace listing as a prerequisite for any "install works" claim; write docs as "intended marketplace path + honest local/dev loaders" without inventing a third install UX. Cursor's folder picker and Claude's durable install are marketplace-shaped; `~/.cursor/plugins/local/` and `claude --plugin-dir` are the real pre-marketplace story. QA clean; suite stayed green.

#### m2 — Marketplace entries in txrk9-agent-plugins (L2)

Added `stockroom` to both Cursor and Claude marketplace catalogs in `txrk9-agent-plugins` (thin name + github source + description; no version pin; prior entries preserved). Opened and later merged [PR #2](https://github.com/Texarkanine/txrk9-agent-plugins/pull/2). README left as URL-add docs. Preflight TDD amendment: fail-then-implement per harness on ephemeral JSON asserts. Product commit lived in the marketplace repo; memory-bank tracking stayed in stockroom. Live install remained m3. QA found nothing to fix.

#### m3 — Release-please exercise + clean-machine E2E spine (L3)

Verified release-please lockstep (tags `v0.1.0` / `v0.1.1`; PR #11 synced both plugin manifests + `.release-please-manifest.json` + CHANGELOG). Operator-driven same-host marketplace install on both harnesses; `sr-initialize` populated the warehouse with real Cursor and Claude history; four surfaces proven via CLI and skill slash-forms. Creative methodology: agent prepares runbook / operator does UI; same-host + marketplace reinstall rather than a second VM.

Deliberate non-fix: Cursor `sessionStart` dashboard hook filed as [#12](https://github.com/Texarkanine/stockroom/issues/12) (WSL/minimal PATH); Claude SessionStart works; dashboard still reachable via `/sr-dashboard` / `stockroom dashboard`. `STOCKROOM_HOME` isolation skipped because initialize had already populated the default XDG home; marketplace `engine-dir` still proved the install source. Accidental start on a #12 packaging-test fix was reverted after operator correction. QA found nothing to fix.

### Key artifacts created / proven

- README install/usage docs (marketplace path + local/dev loaders + invocation table).
- Marketplace catalog entries in `txrk9-agent-plugins` (Cursor + Claude) → `Texarkanine/stockroom`.
- Release-please lockstep cut through `0.1.1` into both `.cursor-plugin/plugin.json` and `.claude-plugin/plugin.json`.
- E2E clean-machine runbook (operator checklist) proving marketplace install → initialize → four surfaces.
- Roadmap Phase 5 milestones checked; v1 success criteria demonstrated.

### Design decisions of record

- **Marketplace is the primary install story** — local/dev loaders are honest secondary paths, not a fake "manual install" UX.
- **Thin catalog entries** — name + github + description; matching existing entries is the whole correctness bar.
- **Verify don't re-cut** — m3 exercised an already-wired release-please path rather than redesigning versioning.
- **Four-surface gate ≠ sessionStart auto-launch** — manual/CLI dashboard satisfies the product claim; hook PATH is a separate bug (#12).
- **Operator-vs-agent E2E split** — agent prepares evidence/runbook; operator performs harness UI steps to avoid false automation claims.

## TESTING

- **m1**: Documentation + deletion of prose-pin tests; QA clean; full suite green.
- **m2**: Red→green ephemeral JSON asserts per harness catalog; QA clean; marketplace PR review/merge.
- **m3**: Packaging tests green (424 passed, 3 skipped at runbook time); release lockstep verified on tags/PR; operator marketplace install both harnesses; CLI proofs for query/semantic/dashboard; operator skill slash-forms both harnesses; QA bookkeeping match, no code defects.

E2E evidence highlights (from the clean-machine runbook):

- `stockroom doctor probe` → marketplace-cached `engine-dir` under `txrk9-agent-plugins/stockroom/...`
- Query: real `claude` / `cursor` row counts; semantic ranked hits; dashboard HTTP 200 on `:6767`
- Cursor `/sr-*` and Claude `/stockroom:sr-*` forms exercised for all four surfaces

## SYSTEM STATE

What exists now that didn't before (or was unproven):

- **User-facing install/usage docs** describing the marketplace path and honest local/dev loaders, with verified per-harness skill invocation forms.
- **Stockroom in both marketplace catalogs** in `txrk9-agent-plugins`, discoverable via the shared marketplace URL.
- **A cut release path** — release-please has synced a real version into both plugin manifests in lockstep.
- **Demonstrated v1 spine** — marketplace install → `sr-initialize` → four surfaces against real Cursor and Claude Code history.

End-to-end: add `Texarkanine/txrk9-agent-plugins` → install stockroom in each harness → initialize (torch, shim, schedule, warehouse) → use search/semantic/query/dashboard via on-path engine and harness-correct skill forms.

### Acceptance criteria — met

1. Install/usage docs exist and document per-harness invocation forms. ✔
2. Stockroom appears in both marketplace manifests pointing at `Texarkanine/stockroom`. ✔
3. Release-please syncs a version into both plugin manifests. ✔
4. Clean-machine marketplace install demonstrates initialize + four surfaces against real history. ✔
5. Roadmap Phase 5 milestones checked; v1 "clean enough to ship" gate met. ✔

Deliberate open item (not a Phase-5 gate for the four surfaces): Cursor sessionStart auto-dashboard — [#12](https://github.com/Texarkanine/stockroom/issues/12).

## LESSONS LEARNED

- **Marketplace listing is a prerequisite for "install works" claims** — inventing a third install UX or CI-locking prose fights the platform contracts (m1).
- **Thin catalog entries are the elegant form** — if marketplace listing had been assumed from Phase 0, stockroom would still only need these two JSON objects (m2).
- **Four-surface proof ≠ hook auto-launch** — keep product gates and packaging/PATH bugs separate (m3).
- **Cross-repo L4 sub-runs need an explicit commit-split line** — which repo gets the product commit vs the memory-bank commit (m2).
- **When the operator files a bug mid-E2E, treat it as evidence + out-of-scope** unless they ask for a fix — do not auto-enter defect repair (m3).

## PROCESS IMPROVEMENTS

- **Write Phase-5-style docs from day one as marketplace-primary + honest local loaders** — avoid mid-build course correction when "manual install" turns out not to be a first-class end-user path.
- **Reserve packaging tests for real install artifacts** (manifests, hooks, release-please) — not README prose or planning-doc pins.
- **Agent prepares runbook / operator does harness UI** — prevents false automation claims on marketplace install proofs.
- **Plan's conditional defect-repair path should not fire** when a known issue is already tracked and the operator blocks the fix.

## TECHNICAL IMPROVEMENTS

- **Cursor sessionStart dashboard hook (#12)** — WSL/minimal PATH; Claude SessionStart works; surfaces still reachable manually. Natural post-v1 packaging fix.
- **Makefile exact-sync / Torch conflict** — still open from earlier phases; full `make ci` can strip the intentionally out-of-lock Torch install.

## NEXT STEPS

None required for Phase 5 / v1 ship gate. Natural continuations:

- Fix Cursor sessionStart auto-dashboard PATH ([#12](https://github.com/Texarkanine/stockroom/issues/12)).
- Post-v1 roadmap items (recap as a time-series, additional harnesses) already deferred by the brief.

### Million-Dollar Question (across sub-runs)

Had marketplace listing and honest local/dev loaders been assumed from Phase 0, Phase 5 would still be: thin dual catalog entries, docs that refuse a fake third install UX, a verify-don't-re-cut release exercise, and an operator-driven marketplace E2E. The elegant form is no version pin in the marketplace, no CI-locked prose, and a four-surface gate that does not conflate product success with sessionStart auto-launch.
