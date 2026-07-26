# Current Task: fix-dashboard-token-tooltip-overflow

**Complexity:** Level 1

## Fix Summary

- **What broke:** Token breakdown popover used `position: absolute` with vertical centering inside `.table-scroll` (`overflow-x: auto` → vertical scrollport). Hover expanded the sessions panel and introduced a scrollbar; tooltip stayed clipped inside the panel ([#91](https://github.com/Texarkanine/stockroom/issues/91)).
- **Why:** Absolute descendants participate in overflow of scroll ancestors; pairing of overflow axes forced a y-scrollbar.
- **What changed:** Popover is `position: fixed` and placed via `tokenBreakdownPlacement` (prefer below / bleed into Wrapped; flip above near viewport bottom; clamp horizontally). Mount wires `pointerenter`/`focusin` to sync coordinates.
- **Files affected:**
  - `skills/sr-search/src/stockroom/dashboard/static/index.html`
  - `skills/sr-search/src/stockroom/dashboard/static/dashboard-tokens.mjs`
  - `skills/sr-search/tests/test_dashboard_static.py`
  - `skills/sr-search/tests-js/dashboard-tokens.test.mjs`

## Checklist

- [x] Root cause identified
- [x] Failing tests written (placement + CSS escape contract)
- [x] Fix implemented
- [x] Full suite green (`make test`: 676 passed / 4 skipped; 105 JS)
