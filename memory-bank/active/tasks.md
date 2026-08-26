# Task: dashboard-subagent-pills

* Task ID: dashboard-subagent-pills
* Complexity: Level 3
* Type: feature

Surface warehouse-linked subagent sessions as distinct inline pills in the dashboard conversation reconstruction, plus a `parent:` line on subagent views.

## Open Questions

- [x] **Spawn-to-turn association** → Resolved: Claude provenance join + Cursor typed-Task zip at read time in `session_detail` (see `memory-bank/active/creative/creative-spawn-association.md`).
- [ ] **Subagent pill chrome** — What does the pill show (heading vs link-only, which label), and how does it sit in the transcript visually?
  - Why ambiguous: operator asked to design-shop heading vs link; warehouse labels differ by harness (`agent_type`, `agent_name`, `title`, Task `description`).
  - Constraints: left-aligned with extra left padding; slightly different color from message pills; clickable to the child reconstruction; do not inline child history. Parent chrome is already decided: `parent:` under the session metadata line, linking to the parent at the child's pill hash.
