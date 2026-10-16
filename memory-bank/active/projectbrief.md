# Project Brief

## User Story

As a stockroom dashboard user, I want a Cursor subagent launch to show the normal inset when the parent calls Task through CallDynamicTool, so I can see and open that child the same way I do for a native Task launch and for a Claude subagent.

## Use-Case(s)

### CLI chat whose child names its parent

The parent turn is a `CallDynamicTool` whose arguments are namespace `cursor` and tool name `Task`. The child chat is already in the warehouse and its store metadata `subagentInfo` names this parent (`parentAgentId`, `toolCallId`, `typeName`). The example is message 42 of Cursor session `5fa10c9d-2c18-42d6-b491-41503d6dc01b`, whose child is `43b093cd-f419-4bee-b60b-56d1f5075d0c`.

### The same wrapper on other Cursor transcripts

A parent can call Task through `CallDynamicTool` on IDE transcripts as well as CLI chats. Those launches get the same inset.

### Claude subagents

Claude sessions that already show the inset, such as `6e0ed576-a814-4406-89e5-73360c6a98de`, keep showing it.

## Requirements

1. A Cursor parent turn that launches a subagent by calling Task through `CallDynamicTool` shows the normal dashboard subagent inset.
2. For a CLI child whose `subagentInfo` names the parent, the inset points at that child.
3. Native Cursor Task launches keep their current insets.
4. The Claude inset path stays as it is.

## Constraints

1. The inset is the existing subagent pill (`#msg-N-sa-M`), including its link to the child session.
2. The example CLI child is already stored. The work attaches the inset to that stored child.

## Acceptance Criteria

1. Message 42 of Cursor session `5fa10c9d-2c18-42d6-b491-41503d6dc01b` shows a subagent inset for child `43b093cd-f419-4bee-b60b-56d1f5075d0c`.
2. A Cursor parent turn that calls Task through `CallDynamicTool` gets an inset when a matching child exists, on both CLI chats and IDE transcripts.
3. Existing native Task insets and Claude spawn-id insets still appear.
