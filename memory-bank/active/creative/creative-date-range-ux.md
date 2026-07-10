# UI/UX Decision: Date-Range Control UX

## User & Context

- **Users:** Local stockroom operators (developers) viewing the offline metrics dashboard on loopback.
- **Task:** Choose a time window so KPIs, charts, and (when bounded) sessions reflect that window; prior-period % deltas follow an equal-length prior window.
- **Context:** Top `.controls` strip beside harness multi-select and Aggregate/Compare. Date range is a query filter (refetch); mode remains presentation-only (render).
- **Constraints:** Fully offline (no calendar library/CDN); fit the existing controls row; keyboard/screen-reader exclusive selection; empty/invalid ranges must not flash partial snapshots; Wrapped stays unfiltered; WCAG-minded contrast/focus within existing dashboard tokens.

## Design System

Authority: shipped static surface under `skills/sr-search/src/stockroom/dashboard/static/` (`index.html` CSS variables, fieldset/radio control patterns, `.controls` layout). No external Figma/Storybook. New control must match existing fieldset + exclusive radio affordances (same family as mode selector after #5 restyle).

## Options Evaluated

- **A — Preset exclusive control (with Default/unset):** Segmented or radio group: `Default` | `7d` | `30d` | `90d` | `1y`. `Default` omits `since`/`until` (honest per-endpoint defaults + current panel copy). Other presets always send both bounds (`until≈now`, `since=until−duration`).
- **B — Free-form from/to date inputs:** Two native `<input type="date">` fields; operator picks arbitrary inclusive start / exclusive-or-end-of-day end. Always custom math for validation and labels.
- **C — Hybrid presets + Custom:** Presets as in A, plus a Custom choice that reveals from/to inputs. Maximum flexibility; densest chrome.

## Analysis

| Criterion | A Presets + Default | B Free-form dates | C Hybrid |
|-----------|---------------------|-------------------|----------|
| Usability | Fast one-click windows matching common ops questions | Flexible but slower; easy to pick invalid/empty ranges | Flexible + fast, but two interaction modes |
| Clarity | Labels map 1:1 to selection; prior-window math obvious | Labels need formatted date spans; easy to misread TZ | Clear when preset; Custom adds cognitive load |
| Accessibility | Same radiogroup pattern as mode; excellent keyboard | Native date inputs vary by browser/OS a11y | Two widgets; focus management harder |
| Consistency | Matches mode fieldset/segment pattern in `.controls` | Diverges from exclusive-toggle visual language | Mixed patterns in one strip |
| Feasibility | Pure HTML/CSS/JS; ISO bounds trivial | Native inputs OK offline, but validation + ISO/TZ edge cases | Most code + tests |
| Simplicity | Smallest surface that meets “selectable range” | Meets “picker” language but overshoots product ask | Overbuilt for m1 |
| Design system | Highest adherence | Acceptable but visually foreign | Crowds the strip |

Key insights:
- Issue #4’s product ask is “selectable range in that control strip,” with UX deferred; L4 preflight already advised presets with clean prior-window math.
- Server prior-window is equal-length immediately before the active window — presets of fixed duration make that operator-obvious (7d → prior 7d, 1y → prior 1y).
- Accepting “unset/Default” preserves today’s mixed endpoint defaults (14d daily / 12w weekly / 30d KPIs) and satisfies “honest defaults when unset.”
- Free-form calendar can land later without rewiring `buildRequestPlan` if the state shape is `{ since, until } | null`.

## Decision

**Selected**: Option A — Preset exclusive control with `Default` (unset)
**Rationale**: Best usability/clarity/a11y/feasibility fit for a dense offline controls strip; matches existing exclusive-control patterns; makes prior-period deltas honest and predictable; preserves current default panel behavior until the operator opts in.
**Tradeoff**: No arbitrary calendar ranges in m1 (operators who need a custom span use a covering preset or wait for a later enhancement). No URL sync or localStorage persistence in m1 (ephemeral per page load).

## Implementation Notes

- **Presets:** `default` (omit bounds) | `7d` | `30d` | `90d` | `1y`. Initial selection: `default`.
- **Bound encoding:** When not `default`, compute `until = now` (ISO) and `since = until − duration`; always send both query params. Never send partial bounds from the UI.
- **Markup:** Prefer `fieldset` + exclusive radios (same a11y model as mode), styled to sit in `.controls`; disable during `aria-busy` like mode/harness.
- **State:** `transitionViewState` gains a `daterange` (or `window`) action → `effect: "refetch"`. Store selected preset id plus resolved `{ since, until } | null`.
- **Labels:** When `default`, keep current per-panel default copy (and overview aria “Thirty-day…”). When preset active, update all `.panel-range` (and overview aria) from the selection (e.g. “Last 7 days” / “Last 1 year”); trends daily+weekly share the same window when bounds are set — label both honestly to that window, not the old 14d/12w defaults.
- **Sessions:** When bounds present, include them on `/api/sessions` (windowed recent-N); when `default`, omit bounds (current open-ended recent-N).
- **Wrapped:** Never attach bounds.
- **Validation:** Preset path has no empty range; if future custom lands, validate before refetch. Client still relies on atomic snapshot gate for HTTP 400.
- **Out of scope m1:** URL query sync, localStorage, free-form calendar, relative “month to date” presets.
- **#5 (companion):** Separate visual restyle of mode radios into one segmented pill; not part of this decision beyond sharing the exclusive-control visual language.
