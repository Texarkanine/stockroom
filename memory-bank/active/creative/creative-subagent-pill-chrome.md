# UI/UX Decision: Subagent Pill Chrome

## User & Context

Power users reconstructing a conversation on the local dashboard. They can already see a `Task` tool block (and skills in the composition doughnuts) but cannot jump to the child transcript. The same people, once inside that child, need a one-click return to the exact spawn pill in the parent.

This chrome lives in the existing session view: overview card (SESSION metadata + composition) above the messages card (turns). It must not compete with `#msg-N` turn pills or look like another tool `<details>`.

## Design System

Authority is the shipped session surface in [`skills/sr-search/src/stockroom/dashboard/static/index.html`](../../../skills/sr-search/src/stockroom/dashboard/static/index.html) and [`dashboard.mjs`](../../../skills/sr-search/src/stockroom/dashboard/static/dashboard.mjs): dark/light tokens (`--page`, `--surface-soft`, `--accent`, `--muted`, `--border`), 90%-width `.session-turn` cards (assistant start / user end), uppercase `.session-turn-role`, muted ordinal links, `.session-meta` as a single muted line under the SESSION label.

No Figma/Storybook. New chrome must reuse those tokens and the existing `<a>` / focus-visible pattern — no new typefaces, no new color variables unless a one-token tint is required for distinction.

## Options Evaluated

- **A. Chip inside the launching turn**: A small pill in the turn heading or after the `Task` `<details>`, same card as the assistant message. Compact; easy to miss; fights the tool list; inherits the turn's `#msg-N` scroll target.
- **B. Sibling inset card**: After the launching turn, a narrower left-aligned card with extra left padding and a tinted surface. Heading is the child's label; the card (or an explicit link) goes to the child reconstruction. Own id `#msg-{ordinal}-sa-{n}`.
- **C. Transcript-top child list**: A list of all children above the first turn (plus the parent line). Easy to scan; loses "this spawn happened here"; fails the inline-under-the-launcher requirement.

Parent chrome is not in play — operator already placed it: a `parent:` line directly under the session metadata row.

```
Option B sketch (assistant turn, then inset):

  ┌──────────────────────────────────────────┐
  │ ASSISTANT                          #48   │
  │ …                                        │
  │ ▸ Task { description, subagent_type }    │
  └──────────────────────────────────────────┘
      ┌────────────────────────────────┐
      │ generalPurpose                 │
      │ Open conversation              │
      └────────────────────────────────┘
```

## Analysis

| Criterion | A. Chip in turn | B. Sibling inset | C. Top list |
|-----------|-----------------|------------------|-------------|
| Usability | One more control in a crowded card | Click target is obvious; sits where the spawn happened | Fast roster, wrong place |
| Clarity | Looks like another tool | Different color + indent = not a message | Severs spawn from turn |
| Accessibility | Nested interactive inside a long article | Own landmark-ish article + single link | Extra list, still need in-transcript targets |
| Consistency | Matches tool chips, not turns | Same card language as turns, distinct tint | New IA above the transcript |
| Feasibility | Small DOM change | Small DOM + CSS; hash helper already exists | Easy, misses the brief |
| Design system | Reuses turn internals | Reuses turn tokens with `color-mix` | Reuses session-meta |

Key insights:

- Operator already specified left-align, extra left padding, and a slightly different color. Option B is that description.
- Inlining child history was explicitly refused; Option B's heading is a label, not a preview.
- `#msg-48` must remain the turn. The spawn needs its own element id, so the pill cannot be a decoration inside `#msg-48` if we also want `#msg-48-sa-1` to scroll to the pill (scrolling the parent turn would hide the distinction).
- Cursor titles are often NULL; the useful name is `agent_type` or the launching Task `description`. Label fallback is a display rule, not a second association algorithm.

## Decision

**Selected**: Option B — sibling inset card under the launching turn, plus the already-chosen `parent:` line under session metadata.
**Rationale**: It is the operator's placement, it keeps `#msg-N` stable, and it gives the spawn its own scroll target and color without inventing a new page region.
**Tradeoff**: A turn that launched several children grows several inset cards (acceptable; `sa-n` exists for that). Unmatched leftover children (algorithm fallback) use the same chrome under their fallback turn — they will look like they belong to that turn.

## Implementation Notes

- Render each `message.subagents[]` entry as an `<article class="session-subagent">` **after** that message's `.session-turn` (sibling in `#session-turns`), not inside the turn.
- `id="msg-{ordinal}-sa-{spawn_index}"`. `scroll-margin-top` matches turns.
- **Label** (heading text), first non-empty: launching Task `description` (pass through from the matched tool_input on the server as `label`), `agent_name`, `title`, `agent_type`, else `"Subagent"`. Server sends `label` so the client does not re-parse tool JSON.
- Heading is visible text; a single `<a>` ("Open conversation") is the reconstruction link (`?view=session&harness=&session=` of the child, no hash). The whole card may be wrapped or the heading may also be the link — prefer **one** focusable link per pill (heading-as-link, no second "Open" control) so keyboard users do not tab twice.
- CSS: `align-self: flex-start`; width ~70–80%; `margin-left: 1.5rem`; background `color-mix(in srgb, var(--accent) 6%, var(--page))`; border `color-mix(in srgb, var(--accent) 40%, var(--border))` — readable in light and dark, distinct from `.session-turn-assistant` (`--surface-soft`) and `.session-turn-user` (10% accent on `--surface`).
- Parent chrome: `<p class="session-parent">` immediately after `#session-meta`, only when `is_subagent`. Content: muted `parent:` + `<a>` to the parent session. `href` includes `#msg-{message_ordinal}-sa-{spawn_index}` when `parent_spawn` is present; otherwise the parent session with no hash. Link text is the parent `session_id` (titles are often null).
- Hash helpers: keep `parseMessageHash` as `^#msg-(\d+)$` only. Add a sibling parser for `^#msg-(\d+)-sa-(\d+)$`. `resolveMessageAnchorElement` becomes a general fragment resolver (or gains a twin) so boot/hashchange can scroll either target.
- `buildSessionDeepLink` gains an optional `spawnIndex` that appends `-sa-N` only when both ordinal and spawn index are valid integers `>= 1` for spawn (ordinal may be 0).
- Do not add subagent pills to markdown/JSON export in this task (not requested; exports stay the current conversation body).
- Do not list children on the sessions browse view.
