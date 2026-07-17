# UI/UX Decision: Skill Usage Mockup Chart Set

## User & Context

**Users**: Local stockroom operators reviewing their own agentic-coding history on the offline dashboard.

**Task**: Visually compare several chart encodings of skill × invoker × harness so the operator can pick one for permanent placement next to Tool Usage ([#63](https://github.com/Texarkanine/stockroom/issues/63)).

**Context**: Main metrics view, Aggregate/Compare toggle already global. Mockups sit in the existing 2-column `chart-grid` as ordinary `.panel` tiles (same 1×1 as Tool Usage). Final layout reshuffle is out of scope for this pass.

**Constraints**: Chart.js 4.5 vendored only; keyboard/tooltip parity with existing panels; harness colors from existing palette; invoker must remain legible in compare mode (four stacks problem called out in the issue).

## Design System

Authority: shipped dashboard static surface (`skills/sr-search/src/stockroom/dashboard/static/` — Chart.js panels, harness color assignment, Aggregate/Compare). No external design kit. Mockups must reuse `panel` / `panel-header` / chart-wrap patterns and existing `PALETTE` / harness color helpers.

## Options Evaluated

Candidate *sets* of mockups to ship (not final chart pick):

- **Set A — Issue-faithful trio**: (1) nested doughnut skills-outer / invoker-inner; (2) horizontal stacked bar skill×invoker; (3) tools-like doughnut aggregate + stacked bar compare with invoker as alpha/hatch on harness hue.
- **Set B — Bar-heavy**: only stacked and grouped bars (no rings) for easier compare-mode parity.
- **Set C — Maximal gallery**: A plus a fourth “small multiples” panel (one mini chart per harness).

Aggregate sketches: nested doughnut (outer=skill, inner=invoker); horizontal stacked bar (Y=skill, stacks=user/agent); tools-like doughnut by skill with invoker in tooltip.

Compare variants: nested uses dual rings or harness-colored outer (weaker); stacked and tools-like use Y=skill with stacks=`harness×invoker` (hue=harness, alpha=invoker).

## Analysis

| Criterion | Set A | Set B | Set C |
|-----------|-------|-------|-------|
| Usability | High — covers ring + bar families from issue | Medium — misses ring preference in #63 | High but crowded |
| Clarity | Good if panels titled clearly | Clear but less exploratory | Risk of decision fatigue |
| Accessibility | Chart.js canvas — same as today; titles must name encoding | Same | Same; more chrome |
| Consistency | Matches Tool Usage panel chrome | Same | Same |
| Feasibility | Nested doughnut needs custom dataset build; doable | Easiest | Extra layout work |
| Simplicity | Three panels = enough signal | Under-serves issue ask | Overkill for mockup phase |

Key insights:
- Operator explicitly wants mockups before choosing; shipping only bars would pre-empt the ring option in #63.
- Compare mode is the hard part; stacked bar with harness hue + invoker alpha is the most honest encoding for four stacks.
- Nested doughnut compare is weaker — acceptable as an aggregate-first mockup that degrades to dual rings or a note in compare.

## Decision

**Selected**: Set A — Issue-faithful trio.

**Rationale**: Directly answers the visual alternatives named in #63 (nested rings vs stacked bars vs tools-like with derivative invoker styling) without flooding the grid. Each panel must honor Aggregate and Compare.

**Tradeoff**: Nested-doughnut compare will be imperfect vs bars; that contrast is useful for the pick, not a bug.

## Implementation Notes

Ship three panels immediately after `#tools-panel` (or at end of chart-grid — order secondary; same 1×1 size):

| Panel id | Title | Aggregate | Compare |
| --- | --- | --- | --- |
| `skills-nested-panel` | Skill Usage (nested) | Doughnut/pie: outer=skill, inner=invoker share | Dual charts or grouped nested by harness (harness color on outer segments; invoker on inner) — keep readable over perfect geometry |
| `skills-stacked-panel` | Skill Usage (stacked) | Horizontal stacked bar: Y=skill, stacks=user/agent | Horizontal stacked: stacks=`{harness}·{invoker}` with harness base color; agent = full opacity, user = ~0.55 alpha (or dashed border) |
| `skills-tools-like-panel` | Skill Usage (tools-like) | Doughnut by skill (totals); legend or tooltip breaks down invoker | Same stacked encoding as stacked panel (proves tools-panel mental model) |

Shared:
- Empty state when no skill events in window (reuse `#tools-empty` pattern).
- Panel titles include `(mockup)` suffix so they are obviously temporary.
- Help text one-liner under title explaining the encoding.
- No new npm/Chart.js plugins; nested doughnut = two datasets with cutout/radius stacking, else two canvases in one panel.

After operator picks: follow-up removes the other two panels and places the winner next to Tool Usage with layout reshuffle from #63.
