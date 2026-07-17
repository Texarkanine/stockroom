# Task: dashboard-skill-sunburst-rework

* Task ID: dashboard-skill-sunburst-rework
* Complexity: Level 2
* Type: simple enhancement (rework)

Rework nested skill mockup into an aligned sunburst, fix stacked tooltip swatch colors, and rename Tool/Skill panels to parallel **Distribution (top 10)** wording.

## Test Plan (TDD)

### Behaviors to Verify

- Sunburst aggregate: outer data ordered user-skills then agent-skills; inner `[userTotal, agentTotal]`; `sum(outer user) === inner[0]` and `sum(outer agent) === inner[1]`
- Sunburst aggregate: skill present for both invokers → two outer segments (one per group)
- Sunburst colors: agent inner = PALETTE[0]; agent skills ranked by agent count get PALETTE[1..]; user-only skills get next free slots; user side = `colorWithAlpha(..., 0.55)` of the same assignment
- Sunburst empty: no skill calls → `empty: true`
- Sunburst compare: still stacked harness×invoker bar (unchanged encoding; colors still agent-full / user-faded)
- Tooltip swatch helper / chart options: stacked skill datasets report tooltip `labelColor` fill === dataset `backgroundColor` (not borderColor)
- Titles: Tool Distribution panel heading includes `(top 10)`; skill mockup headings use `Skill Distribution` + encoding cue + `(top 10)` + `(mockup)`
- Static smoke: panel ids unchanged; title strings / aria-labels updated
- Regression: existing extractor and `metrics.skills` tests remain green

### Edge Cases

- All user, zero agent → inner agent arc 0 (or omit zero-length carefully); colors still assign from agent-rank rules then user-only fallbacks
- All agent, zero user → symmetric
- Single skill only on user side → gets next palette after agent group color
- Limit/top-10: titles say top 10 even when fewer skills returned

### Test Infrastructure

- Framework: Node 22 built-in test runner (`make test-dashboard-js`); pytest for static (`make test-dashboard-py`)
- Test location: `skills/sr-search/tests-js/dashboard-core.test.mjs`, `skills/sr-search/tests/test_dashboard_static.py`
- Conventions: existing `buildSkills*Panel` / `assertDataset` helpers; static HTML id/title assertions
- New test files: none (extend existing)

## Implementation Plan

1. **Sunburst model tests (failing) then rebuild `buildSkillsNestedPanel` aggregate** ✅
   - Files: `tests-js/dashboard-core.test.mjs`, `static/dashboard-core.mjs`
   - Changes: rewrite aggregate path to emit sunburst datasets — outer labels/data as user-group skills then agent-group skills; inner `[userTotal, agentTotal]`; set `innerLabels`; agent-led `backgroundColor` assignment using existing `PALETTE` + `colorWithAlpha`; keep compare → stacked bar
   - Helper (same file): e.g. `assignSkillSunburstColors(agentCountsBySkill, userOnlySkills)` if it keeps the builder readable

2. **Tooltip swatch parity — failing helper test then wire** ✅
   - Files: `tests-js/dashboard-core.test.mjs`, `static/dashboard-core.mjs`, `static/dashboard.mjs`
   - TDD: add failing unit test for `tooltipLabelColors(dataset, dataIndex)` (or equivalent) asserting fill comes from `backgroundColor` not `borderColor`; implement helper; wire `plugins.tooltip.callbacks.labelColor` in `chartOptions` to the helper
   - Applies to stacked skill compare (and other panels sharing `chartOptions`) so legend/bar/tooltip match

3. **Distribution (top 10) titles — failing static assertions then markup**
   - Files: `tests/test_dashboard_static.py`, `static/index.html`, `static/dashboard.mjs`
   - TDD: extend failing assertions that Tool panel title contains `top 10` and skill panel titles use `Skill Distribution` + `top 10` + `mockup`; then update `index.html` headings/aria-labels/encoding blurbs and any hardcoded `renderChart` title strings in `dashboard.mjs`

4. **Verify**
   - Files: none new
   - Changes: `make test-dashboard-js` + `make test-dashboard-py`; `make local-dashboard` for operator visual check
   - Docs: skip user-guide (no endpoint catalog); no API docs change

## Technology Validation

No new technology - validation not required (Chart.js already vendored; sunburst = two doughnut datasets with shared circumference ordering).

## Dependencies

- Existing `/api/skills` payload shape `{skills, invokers, calls}` — no server change
- `PALETTE`, `colorWithAlpha`, `SKILL_INVOKERS`, `chartInteractionOptions(..., "doughnut")` already in tree
- Default metrics `limit=10` matches title copy `(top 10)`

## Challenges & Mitigations

- **Chart.js legend lists every outer skill twice (user+agent)**: Mitigation — prefer legend on inner invoker datasets only, or custom legend labels `"{skill} · {invoker}"`; keep tooltips authoritative for segment identity
- **Zero-length inner arc (all-user or all-agent)**: Mitigation — still emit both inner values (0 allowed); Chart.js skips empty arcs; document in test
- **Tooltip `labelColor` vs pointStyle legend**: Mitigation — set both fill and stroke in `labelColor` to the bar fill so swatches cannot pick `borderColor`
- **Title drift if limit changes later**: Mitigation — comment next to HTML titles that copy tracks `skills()`/`tools()` default `limit=10`; out of scope to plumb limit into the client

## Pre-Mortem

- **Wrong premise: treat sunburst as two independent pies with shared colors only** → Plan response: Step 1 asserts circumference alignment (`sum` equality) so mis-ordered outer data fails tests
- **Tooltip fix regresses project/tools panels** → already covered by Challenge: scope `labelColor` to use backgroundColor consistently (safe for single-color datasets)
- **Rename without static test updates** → Step 3 includes `test_dashboard_static.py` title assertions

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Pre-Mortem complete
- [x] Preflight — PASS (TDD encoding tightened on steps 2–3; `renderChart` title strings confirmed in plan)
- [ ] Build
- [ ] QA

## Preflight Amendments

- Steps 2–3 now state failing tests before production edits (`tooltipLabelColors` helper; static title assertions).
- Confirmed `dashboard.mjs` hardcodes `renderChart` titles (`Tool distribution`, `Skill usage …`) — must update alongside HTML.
