# UI/UX Decision: Per-Page Control on Sessions List

## User & Context

**Users:** Local operators (and agents constructing URLs for those humans) browsing agentic-coding history on localhost.

**Task:** Choose how many session rows to show per page on the sessions-list view, including an explicit “show everything in this filter range” mode.

**Context:** Replaces Aggregate/Compare in the top control bar of a new `view=sessions` pane. Harnesses + time range stay; pagination chrome sits above and below the list when paging is active. Row click → existing reconstruct view; browser Back is the only back navigation.

**Constraints:** Offline static SPA; keyboard-accessible; match existing control density; URL-owned (`per_page`); API maps show-all → `limit=0`.

## Design System

Authority is the shipped dashboard static surface (`skills/sr-search/src/stockroom/dashboard/static/`): radio groups for date range and Aggregate/Compare (`#mode-selector`), `<details>` harness picker, plain tables for session rows. No external design kit. New control should read as a sibling of `#mode-selector`, not a foreign widget.

## Options Evaluated

- **A — Radio presets (25 / 50 / 100 / All):** Same interaction model as Aggregate/Compare; All is the last radio. URL: `per_page=25|50|100|all`.

```
[ Harnesses ▾ ] [ ○7d ○30d … ] [ ○25 ○50 ○100 ○All ]
```

- **B — `<select>` with presets + All:** One compact control; All last option. URL same as A. Custom typing not included.

```
[ Harnesses ▾ ] [ ○7d ○30d … ] [ Per page ▾ 50 ]
```

- **C — Presets + custom number:** Radios or select for presets, plus a number field for arbitrary sizes. URL: `per_page=<int>|all`.

```
[ … ] [ ○25 ○50 ○100 ○Custom [___] ○All ]
```

## Analysis

| Criterion | A Radios | B Select | C + Custom |
|-----------|----------|----------|------------|
| Usability | Familiar; all options visible | Fine; one extra click to see options | Most flexible; more chrome |
| Clarity | Highest — matches mode radios | Label needed (“Per page”) | Custom path easy to mis-set |
| Accessibility | Native radios / fieldset like mode | Native select OK | More focus stops / validation |
| Consistency | Best match for the slot | Slightly foreign in that bar | Heavier than sibling controls |
| Feasibility | Trivial | Trivial | Extra parse/validate |
| Simplicity | Best | Good | Overkill for localhost |

Key insights:
- Issue requires show-all at the **bottom of the control** — radios make “bottom” literal and visible; a select’s last option also works but hides All until opened.
- Operator preference is tall pages / All is fine — fixed presets do not need a custom path for v1.
- Agents constructing URLs benefit from a small closed set of `per_page` tokens.

## Decision

**Selected**: Option A — radio presets **25 / 50 / 100 / All**, with All last.

**Rationale:** Strongest consistency with the Aggregate/Compare control it replaces; All is always visible at the bottom of the group; closed URL vocabulary is agent-friendly; no validation surface for free-typed sizes.

**Tradeoff:** No arbitrary page sizes (e.g. 40). Acceptable — 25/50/100 + All cover glanceable paging and the explicit full dump.

## Implementation Notes

- Markup: `#per-page-selector` (or reuse `#mode-selector` slot on the list pane only) with `name="per-page"` radios: `25`, `50`, `100`, `all`. Default **50** when `per_page` missing/invalid.
- Visible only on sessions-list pane; metrics pane keeps Aggregate/Compare unchanged.
- URL: `per_page=25|50|100|all`. Changing per-page resets `page=1` (or omits page when 1).
- Fetch mapping: `all` → API `limit=0` (no OFFSET needed, or `offset=0`); numeric → `limit=N&offset=(page-1)*N`.
- Pagination chrome (prev/next + “Page X of Y” or equivalent): shown top and bottom only when `per_page !== all` and `total > per_page`.
- Keyboard: same as existing radio groups; no new pointer-only widgets.
- Label the group accessibly (e.g. `fieldset` + `legend` “Per page” or `aria-label` on the group), matching how mode/date groups are exposed today.
