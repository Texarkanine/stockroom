# Progress

Show friendly project names with `project_id` on hover (#8) and add clickable info-icon tooltips for Session Efficiency and First-Prompt Quality (#7).

**Complexity:** Level 3

## 2026-07-10 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - Advanced L4: m2 checked off; classified next unchecked milestone (m3: #8 + #7) as Level 3
* Decisions made
    - Not a bug fix; enhancement spanning metrics/display contract + accessible tooltip chrome across panels → multiple components → L3
    - Aligns with milestones.md advisory estimate for m3
* Insights
    - Friendly names are display-only; `sessions.project_id` remains the grouping/identity key
    - Tooltips are limited to Session Efficiency and First-Prompt Quality only

## 2026-07-10 - PLAN - COMPLETE

* Work completed
    - Component analysis across metrics.py, dashboard-core, dashboard.mjs, index.html, tests
    - TDD plan: projects labels + sessions/wrapped project_id + panel labelTitles + two-panel help chrome
    - No open questions; no new dependencies
* Decisions made
    - Keep `projects` as ranked ids; add parallel `labels`; cwd = most recent non-NULL in window
    - Chart.js tooltip (not tick DOM) for slug hover; `title` attrs on sessions/marathon
    - Static `PANEL_HELP` copy; info icons only on efficiency + first-prompt
    - Dirty trends/writeShare WIP is out of scope — restore before build
* Insights
    - Widening `_session_rows` would ripple overview/trends/efficiency — projects-local cwd pass is safer

## 2026-07-10 - PREFLIGHT - COMPLETE

* Work completed
    - Validated plan against metrics/static/core/adapter; TDD encoding amended; `.preflight-status` = PASS
* Decisions made
    - Keep projects-local cwd resolution; Chart.js tooltip for slug hover; pure helpers for help toggle
* Insights
    - `_seed_session` needs `cwd=` for #8 fixtures; existing projects exact-assert must grow `labels`

## 2026-07-10 - BUILD - IN-PROGRESS

* Work completed
    - Restored out-of-scope trends/writeShare dirty WIP to HEAD before implementation
    - Synced plan text to operator amendment of cwd-disagreement rule
* Decisions made
    - **cwd pick when sessions disagree**: show the full `project_id` if there is not one unique short name (replaces most-recent non-NULL cwd)
* Insights
    - Unique short name = all non-NULL cwds for a ranked `project_id` share one basename; otherwise label equals id

## 2026-07-10 - BUILD - COMPLETE

* Work completed
    - Steps 1–7: projects `labels` + `project_display_name`, sessions/wrapped `project_id`, panel `labelTitles`, Chart.js/session/marathon hover, `PANEL_HELP` + two-panel info chrome, help toggle
    - `make ci` green: ruff, 48 JS tests, 485 pytest passed / 3 skipped, REUSE compliant
* Decisions made
    - Applied operator unique-short-name rule; series alignment stays on ranked ids while chart ticks use friendly labels
* Insights
    - Projects-local cwd query avoided widening `_session_rows`; help copy stays static in JS with thresholds documented against Python constants
