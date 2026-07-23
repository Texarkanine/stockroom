# Progress

Fix Cursor `sessions.models` cliff (#82): walk/merge all readable `ai-code-tracking.db` candidates (fail-soft), optional additive XDG `ai_tracking_dbs`, keep `STOCKROOM_AI_TRACKING_DB` as single-DB override; ship on `wsl-dual-sot` without reviving aborted vscdb token enrich.

**Complexity:** Level 2

## 2026-07-22 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - Confirmed Fresh memory-bank state; clarified intent against #82 and aborted `enhance-cursor-tokens` archive
    - Classified as Level 2 (multi-component bug fix / contained enrichment subsystem change)
* Decisions made
    - Work on `wsl-dual-sot`, not `enhance-cursor-tokens`
    - Create XDG config fresh if needed; reference aborted branch only for XDG shape
    - Explicitly out of scope: state.vscdb token enrich, Claude token ingest, #84 backfill
* Insights
    - Root cause is first-hit path resolution with disjoint conversationId sets, not Cursor stopping model emission

## 2026-07-22 - PLAN - COMPLETE

* Work completed
    - Surveyed enrich.py first-hit resolution, orchestrator apply seam, absent XDG config on this branch
    - Wrote Level 2 TDD plan: resolve/merge path set, fresh config.ai_tracking_dbs, docs, no state_vscdb
* Decisions made
    - Create `resolve_config_home` + `stockroom.config` fresh (aborted branch reference only)
    - Docs-only for operator guidance (no doctor/onboarding UI)
    - Residual "preserve models on total enrich miss" out of #82 acceptance
* Insights
    - Chats `store.db` path does not apply ai-tracking enrichment today — leave unchanged

## 2026-07-22 - PREFLIGHT - COMPLETE

* Work completed
    - Validated plan against enrich/orchestrator/home; amended TDD encoding and orchestrator AC test
    - Wrote `.preflight-status` PASS
* Decisions made
    - Import `stockroom.home` from config (no required warehouse re-export)
    - Docs-only operator surface; optional installed-layout config-home line
* Insights
    - Blocking risk was implementation-first step wording; fixed in-plan before Build
