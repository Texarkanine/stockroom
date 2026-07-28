# Task: dashboard-marathon-link-and-msg-deep-link-investigate

* Task ID: dashboard-marathon-link-and-msg-deep-link-investigate
* Complexity: Level 2
* Type: simple enhancement + investigation

Make the Wrapped "Marathon Session" cell a deep-link to that conversation, and add message-ordinal hash deep-links on reconstruction bubbles.

## Investigation Findings: Message Ordinal Deep-Links

**Verdict: feasible and implemented.** Detail API already exposed `ordinal`; client now uses `#msg-N` with post-render top-of-bubble scroll.

## Implementation Plan

Each step was one TDD cycle. Completed:

1. [x] API: include marathon `session_id`
2. [x] Pure cell model: `sessionLink` identity fields
3. [x] DOM: marathon `<a>` + SPA `openSessionView`
4. [x] Pure helpers: `messageAnchorId` / `parseMessageHash` / `resolveMessageAnchorElement` / deep-link ordinal
5. [x] Ordinal indicators + bubble ids + `scroll-margin-top`
6. [x] Hash scroll after load + `hashchange`
7. [x] User-facing docs (`docs/user-guide/dashboard.md`)

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Pre-Mortem complete
- [x] Investigation (ordinal deep-links) complete
- [x] Operator confirmation: both
- [x] Preflight
- [x] Build
- [ ] QA
