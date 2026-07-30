---
task_id: cursor-beforesubmit-shim-rectify-and-dashboard-recovery-ux
complexity_level: 3
date: 2026-07-30
status: completed
---

# TASK ARCHIVE: Cursor beforeSubmitPrompt Path-Only Rectify + Dashboard Recovery HTML

## SUMMARY

Extended Cursor plugin lifecycle with a trimmed non-blocking `beforeSubmitPrompt` suspenders path that background-runs path-only shim rectify (skip `ensure_engine_env`; keep full `sessionStart`; no `workspaceOpen`), and replaced bare JSON 404s on dashboard static/document misses with one in-memory diagnostic HTML page. Operator MVP descoped a shim-vs-replace classifier before build. Post-reflect rework made the recovery page harness-first (`/sr-dashboard` → `/sr-initialize`) with a dedicated troubleshooting section, and CI forced a loose-text-oracle fix on the traversal-guard test. Shipped via [PR #110](https://github.com/Texarkanine/stockroom/pull/110) (merged as `f7a3b8f`).

## REQUIREMENTS

From the project brief:

1. Add a Cursor-only `beforeSubmitPrompt` hook that runs a heavily trimmed, non-blocking path-only `shim rectify` (no dashboard launch; no ensure-env on that path).
2. Keep the existing Cursor `sessionStart` hook (full rectify + dashboard).
3. Do not restore or add `workspaceOpen`.
4. When the dashboard cannot serve real static/UI content, return one in-memory diagnostic HTML page (ordered remedies + online docs links).
5. Diagnostic copy must be shim-first: never present `--replace` as the sole or leading remedy.
6. API/session JSON 404 contracts stay unchanged.

Constraints: must not slow prompt submission; trim aggressively on the hot path; hook doctrine (idempotent, fault-tolerant, `|| true`); Claude hooks out of scope; no classifier in MVP.

Post-reflect rework (operator):

1. Recovery page: harness-first short rundown (new chat → `/sr-dashboard`, then `/sr-initialize` if still broken); no circular `stockroom` CLI / torch tips on the page.
2. Dedicated troubleshooting section `#dashboard-ui-will-not-load` with softer “things that sometimes contribute / things to try” framing.
3. Traversal/static-miss tests must not prose-pin recovery headline English (SLOBAC loose-text-oracle / always-tdd change-detector).

## CREATIVE PHASE DECISIONS

### beforeSubmitPrompt trim (`creative-beforesubmit-rectify-trim.md`)

**Design question:** how to heal the on-path shim when macOS Cursor misses `sessionStart`, without delaying every prompt submit.

**Options:**

- **A — Background full `shim rectify` after continue:** Same heal as sessionStart, detached; still runs `uv sync --check` (+ torch ensure) on every prompt when healthy.
- **B — Continue-first + path-only rectify (skip ensure-env):** Create/rebake shim only; env heal stays on sessionStart / explicit ensure-env / `sr-initialize`.
- **C — Probe-then-heal in-process before continue:** Synchronous cheap header compare; risks blocking if probe/IO stalls.
- **D — Tiny timeout synchronous full rectify:** Relies on fail-open; can stall submit or kill mid-heal.

**Selected: Option B.** Non-blocking and thrash-avoidance outrank completeness of engine env on the hot path. Healthy `ensure_engine_env` still shells `uv sync --check` — too expensive at prompt frequency. Primary macOS miss symptom is missing/stale shim bake (`CURSOR_PLUGIN_ROOT`); env heal is orthogonal.

**Tradeoff:** Cold empty `.venv` after a plugin move may need sessionStart or `sr-initialize`; path-only suspenders do not guarantee env heal.

**Implementation sketch that held:** drain stdin → print `{"continue":true}` → background `{ uv python find; PYTHONPATH=… python -m stockroom shim rectify --path-only; } || true` → exit 0; tiny hook timeout; packaging tests lock continue JSON, `--path-only`, no dashboard, sessionStart still full+300s.

### Dashboard recovery UX (`creative-dashboard-recovery-ux.md`)

**Design question:** what to serve when the dashboard cannot load real UI, without advising `--replace` when the shim is dead.

**Options:**

- **A — Targeted probe with ordered remedies:** Classify shim-dead vs stale-listener vs unknown; hard rule encoded in classifier (shim-dead page omits `--replace`).
- **B — Generic pretty troubleshooting only:** Always same HTML with shim-first ordered commands + docs; no classifier.
- **C — Redirect to docs site only:** Weak offline story.
- **D — Leave JSON 404:** Rejected — ignores accepted recovery-UX requirement.

**Original creative pick: Option A** (B as terminal bucket). **Superseded (operator MVP, 2026-07-30): Option B only** — one generic diagnostic page. Rationale: path-only suspenders leave env-heal undiagnosed; a half-wrong classifier that can still push `--replace` is worse than one honest page. Exact FS classification deferred.

**Friction discovered in implementation / rework:** Initial page copy still leaned on CLI remedies; operator post-reflect rework pivoted to harness skills (`/sr-dashboard`, `/sr-initialize`) because a dead shim makes any `stockroom …` tip circular. Content-contract tests had to move with the copy; a traversal-guard test that substring-pinned the recovery headline failed CI as a loose-text-oracle and was rewritten to assert packaged index bytes + `recovery.render_diagnostic_html()` equality.

## IMPLEMENTATION

**Shim path-only mode**

- `stockroom.shim.rectify(..., ensure_env: bool = True)`; CLI `--path-only` sets `ensure_env=False`.
- Default rectify still calls `ensure_engine_env` (sessionStart unchanged).
- Key files: `skills/sr-search/src/stockroom/shim.py`, `tests/test_shim.py`, `tests/test_shim_cli.py`.

**Cursor beforeSubmitPrompt hook**

- `hooks/cursor-hooks.json`: new `beforeSubmitPrompt` — continue-first, background path-only rectify, small timeout, no dashboard; `sessionStart` remains full rectify + dashboard, timeout 300.
- Packaging tests lock the contract (`tests/test_packaging.py`).

**Diagnostic recovery page**

- New `skills/sr-search/src/stockroom/dashboard/recovery.py`: `render_diagnostic_html()` from in-memory string constants; imported at server module load so a deleted plugin tree cannot remove the page.
- `server.py`: static/document misses (including `/` with missing `index.html`, traversal escapes) serve 404 `text/html` diagnostic; `_not_found()` stays JSON for `/api/*` and missing session.
- Post-reflect page content: harness-first ordered list (`/sr-dashboard` then `/sr-initialize`) + links to `#dashboard-ui-will-not-load` and troubleshooting index.
- Docs: `docs/architecture/lifecycle.md`, `docs/user-guide/dashboard.md`, `docs/user-guide/troubleshooting/index.md` (new `#dashboard-ui-will-not-load` section).
- `memory-bank/systemPatterns.md` reconciled for Cursor beforeSubmitPrompt path-only suspenders.

**CI follow-up**

- `test_static_root_and_traversal_guard`: dropped prose pin on recovery headline; asserts packaged `index.html` bytes + body equals `recovery.render_diagnostic_html()` + no `/etc/passwd` leak.

## TESTING

- TDD throughout per plan steps 1–4 (shim → hook → recovery module → server wire); docs prose without behavior tests.
- New `tests/test_dashboard_recovery.py` (HTML content contracts + HTTP static HTML / API JSON split); extended packaging, shim, shim CLI, dashboard server tests.
- Full suite green at build: 793 passed / 4 skipped Python (`make test`); 119 JS; `make lint` clean.
- `/niko-preflight` PASS (re-validated after MVP amendment). `/niko-qa` PASS — no substantive fixes; non-blocking note on duplicated `_running_server` helper in recovery tests.
- CI engine caught the loose-text-oracle on traversal 404; fixed and saved.
- PR #110 CodeRabbit review (4823809736) flagged broken recovery HTML markup, weak packaging assert, docs conflating prompt with dashboard launch, and MB AC stale vs harness-first page — triage context for follow-ups, not blocking this archive.

## LESSONS LEARNED

- Healthy `ensure_engine_env` still shells `uv sync --check` — path-only vs full rectify is a real frequency split, not premature optimization.
- Recovery HTML must be import-time resident (string constants in a module loaded at process start); reading plugin files on 404 fails exactly when the tree is gone.
- Never convert `_not_found()` wholesale to HTML — `/api/*` and session-miss share that helper with the SPA’s machine contract.
- Dead shim makes on-page `stockroom …` tips circular; harness skills that own `CURSOR_PLUGIN_ROOT` (`/sr-initialize`, `/sr-dashboard`) are the honest first remedies.
- Substring oracles on user-facing recovery English are change-detectors under always-tdd / SLOBAC loose-text-oracle; equality to the renderer (or structural contracts) carries the regression value.

## PROCESS IMPROVEMENTS

- Descoping a clever classifier to one honest page *after* creative but *before* build (with preflight re-validation) was cheaper than discovering false `--replace` advice in QA.
- Existing “rectify always ensures” / “exactly one sessionStart” tests must be deliberately extended, not blindly preserved — call that out in the plan when invariants shift.
- Post-reflect UX rework is fine for L3 when operator UAT changes copy doctrine; keep content-contract tests paired with the page so CI catches drift.

## TECHNICAL IMPROVEMENTS

- Deferred: FS probe / `classify()` for shim-dead vs needs-replace vs env-incomplete (process *can* do some of this while recovery code is still in memory).
- Optional later: flock around background path-only rectify if rapid-submit storms become measurable (v1 accepts idempotent rebakes).
- Recovery HTML markup should stay well-formed (CodeRabbit noted a broken structure in review) — worth a quick fix if still broken on main.

## NEXT STEPS

- Optional: address remaining PR #110 review items if still open after merge (HTML validity, packaging assert strength, docs wording).
- Deferred classifier for shim-dead vs needs-replace remains available as a follow-up when detection is trustworthy enough to short-circuit `--replace`.
- None required to close this task — feature is on main.
