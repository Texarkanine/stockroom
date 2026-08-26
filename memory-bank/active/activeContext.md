# Active Context

## Current Task: dashboard-subagent-pills
**Phase:** REFLECT COMPLETE (post-reflect chrome on PR #126)

## What Was Done
- Built all five plan units (TDD). QA PASS. Reflection written. Persistent files already named both fragment forms.
- Live example: parent `604ead72-0402-49f2-bceb-c22ebed2ec33` / child `bc960b66-605b-4e83-baac-be61435555f5`. One pill on turn 48 (`#msg-48-sa-1`, label `L3 QA 16-hex-leafset`). Untyped Task at msg 55 is not a slot.
- Draft PR: https://github.com/Texarkanine/stockroom/pull/126 (`subagent-insets`).
- Post-reflect chrome (operator live look): outer card matches assistant/user (`SUB-AGENT` role); inner `.session-subagent-convo` is the child link; `margin-left: 1.5rem` + accent wash on `--surface-soft`; heading ordinal `#48-sa-1` (same muted `.session-turn-ordinal` as turns). Merged `origin/main` (`#123` `bindSessionMarkdown` + `#125` CONTRIBUTING). Turn bodies use `markdownRender`, not raw `markdown.render`. Dashboard JS 134 green. In-IDE browser verification was crashy — do not rely on it; hard-refresh `:58008` for `dashboard.mjs`.

## Operator decisions
- **Claude unmatched spawn id:** refuse to guess. No leftover placement.
- **JSON export:** keep `messages[].subagents` and `parent_spawn`. Do not redact.
- **Harness→technique map:** `claude` → provenance join, `cursor` → corroborated zip, unknown → no placements. Comment the map in `spawns.py`: a third harness is the cue to extract the techniques, not another `elif` with Cursor knobs.
- **Pills are positive claims:** omit rather than guess. Missing a pill is acceptable; a pill on the wrong turn is not.

## Cursor corroboration
- Candidates: children with non-null `agent_type`, `source_path` order. Slots: typed Tasks (`_parent_subagent_types`).
- **Aligned zip** only if counts equal and each `child.agent_type == slot.subagent_type`.
- Else **unique type** pairs only (`agent_type` appears once on both sides).
- Extra children, null `agent_type`, count holes with colliding types: omit. No last-Task / last-message leftover.
- Residual: two compensating holes when every remaining pair shares one type still looks aligned. No further warehouse signal.

## Next Step
- Run `/niko-archive` when the operator accepts the chrome on PR #126 (or review/merge the PR first). Do not start a new Niko task on this bank until archive.
