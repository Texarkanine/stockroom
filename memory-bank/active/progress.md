# Progress

Add a Cursor `beforeSubmitPrompt` trimmed non-blocking shim-rectify suspenders path (keep `sessionStart`; no `workspaceOpen`), and improve dashboard recovery UX so users get shim-first / replace guidance — or at least a pretty troubleshooting page — instead of bare JSON 404s after plugin updates.

**Complexity:** Level 3

## 2026-07-30 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - Clarified intent: beforeSubmitPrompt = rectify-only, keep sessionStart, defer workspaceOpen
    - Clarified dashboard recovery: prefer detect shim-needs-rectify vs needs-replace; never advise `--replace` when shim is the problem; pretty troubleshooting fallback OK
    - Determined Level 3 (multi-component: hooks packaging + trimmed heal path + dashboard recovery UX; design decisions required)
* Decisions made
    - Level 3 Intermediate Feature
    - Claude / workspaceOpen out of scope for this task
* Insights
    - Cursor docs: `sessionStart` is fire-and-forget; `beforeSubmitPrompt` can gate send — non-blocking design is load-bearing
    - Full sessionStart payload on every submit was rejected; rectify-only suspenders + keep dashboard on sessionStart

## 2026-07-30 - CREATIVE - COMPLETE

* Work completed
    - OQ1 architecture: continue-first + background `--path-only` rectify (skip ensure-env)
    - OQ2 architecture: ordered recovery classifier; HTML for static/document 404; API JSON unchanged
* Decisions made
    - sessionStart remains sole automatic full ensure+dashboard owner
    - Hard rule encoded as control-flow short-circuit (shim-dead page omits `--replace`)
* Insights
    - Healthy `ensure_engine_env` still pays `uv sync --check` — too thrashy for every-prompt full rectify

## 2026-07-30 - PLAN - COMPLETE

* Work completed
    - Component analysis, TDD map, implementation steps, challenges, pre-mortem written to `tasks.md`
* Decisions made
    - Six implementation steps: shim flag → hook → classifier → server HTML → docs → full suite
* Insights
    - Existing packaging/shim tests assert “exactly one sessionStart” / “rectify always ensures” — must be extended, not blindly preserved

## 2026-07-30 - PREFLIGHT - COMPLETE

* Work completed
    - Validated plan against shim/dashboard/packaging tests and hook doctrine
    - Amended implementation steps for explicit TDD ordering, API/static 404 split, public header reader
    - Wrote `.preflight-status` PASS
* Decisions made
    - Keep `_not_found()` JSON-only; static miss gets a separate HTML recovery path
* Insights
    - `_serve_session` and unknown API share `_not_found()` today — converting that helper would break SPA contracts

## 2026-07-30 - PLAN AMENDMENT - MVP RECOVERY

* Work completed
    - Operator accepted MVP: recognize broken listener → one diagnostic HTML page (ordered remedies + online manual links)
    - Dropped shim-vs-replace classifier and public shim header reader from this task
    - Updated `tasks.md`, `projectbrief.md`, creative recovery doc; preflight re-validated PASS
* Decisions made
    - Exact FS diagnosis deferred; copy must still be shim-first and mention ensure-env (path-only gap)
* Insights
    - Running process can probe more later, but only if recovery code was imported before plugin-dir deletion

## 2026-07-30 - BUILD - IN-PROGRESS

* Work completed
    - Creative decisions re-reviewed (path-only continue-first; one diagnostic HTML page)
    - Preflight confirmed PASS; beginning TDD step 1 (shim path-only)
* Decisions made
    - Build to MVP plan (no classifier)
* Insights
    - (none yet)
