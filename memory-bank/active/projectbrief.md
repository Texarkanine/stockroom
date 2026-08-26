# Project Brief

## User Story

As someone reading a reconstructed conversation in the stockroom dashboard, I want spawned subagent conversations to appear as distinct, clickable pills in the transcript — and a parent link when I am already inside a subagent — so I can hop between parent and child reconstructions without losing the existing message numbering.

## Use-Case(s)

### Parent conversation with spawned subagents

Opening a top-level session such as [604ead72-0402-49f2-bceb-c22ebed2ec33](http://localhost:58008/?view=session&harness=cursor&session=604ead72-0402-49f2-bceb-c22ebed2ec33) shows Task tool calls (e.g. `#msg-48`) but no path to the child session that already exists in the warehouse (`bc960b66-605b-4e83-baac-be61435555f5`). After this work, each spawn gets an inline subagent pill under the launching turn, linking to that child's reconstruction.

### Nested subagent

Opening a child that itself spawned further subagents shows those grandchildren the same way: each conversation only renders *its* children.

### Viewing a subagent conversation

Opening a session that `is_subagent` shows a `parent:` line under the session metadata (harness / model / tokens / started) with a clickable link back to the parent, deep-linked to that child's pill (`#msg-{ordinal}-sa-{n}`).

## Requirements

1. For each conversation, if it spawned one or more subagent sessions, render a visually distinct pill in the transcript for each child that can be associated with a launching turn. A Claude child whose `spawning_tool_use_id` does not join a parent tool is omitted — do not guess a turn.
2. Place each pill inline under the launching turn, left-aligned with a little left padding and a slightly different color from ordinary message pills.
3. The pill is a clickable link to that child's session reconstruction. Do not inline the child's history.
4. Pill heading/label (name vs link-only vs both) is a design-shop decision.
5. Recursion is free: no special grandchild logic beyond "this conversation's children."
6. New fragment anchors so existing `#msg-N` numbering stays stable: `#msg-{ordinal}-sa-{n}` (1-based among children of that turn).
7. When the open conversation is a subagent, show `parent:` under the session metadata line, linking to the parent session deep-linked to that child's pill.
8. Sessions list remains top-level only; this work does not add subagents to the browse list.

## Constraints

1. Warehouse already has the linkage (`sessions.is_subagent`, `sessions.parent_session_id`, `sessions.agent_type`). Do not invent a second parent/child model.
2. Existing `#msg-N` deep links and visible turn numbers must keep working.
3. Read-only dashboard; no ingest rewrite unless spawn-to-turn association cannot be derived from current rows.
4. Offline, committed ES modules under `stockroom/dashboard/static/`; no new front-end dependencies.
5. Claude unmatched spawn ids: refuse to guess. Assume Claude Code provides good data; do not invent a pill for a join that failed.
6. JSON export keeps `messages[].subagents` and `parent_spawn`. Do not redact — export is enough to rebuild a UI in front of the JSON.

## Acceptance Criteria

1. On the example parent session, the Task spawn around message 48 produces at least one subagent pill that opens the child reconstruction.
2. The child reconstruction shows `parent:` under the session metadata line, linking back to the parent at `#msg-48-sa-1` (or the correct `sa-n` if that turn launched more than one).
3. A turn that launched multiple subagents gets `#msg-{ordinal}-sa-1`, `#msg-{ordinal}-sa-2`, … without renumbering ordinary messages.
4. Opening `#msg-N` still scrolls to the existing message pill.
5. Opening `#msg-N-sa-M` scrolls to that subagent pill.
6. No child transcript text is copied into the parent view.
7. A Claude child whose spawn id does not match any parent tool gets no pill.
8. Export JSON includes the new session-detail fields (no redaction).
