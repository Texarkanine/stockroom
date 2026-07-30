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
