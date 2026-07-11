# Project Brief

## User Story

As a stockroom operator (or skill), I want to open a dashboard view that reconstructs a prior conversation by session identifier so that I can inspect the full thread in-place and optionally export it for use elsewhere.

## Use-Case(s)

### Use-Case 1 — Drill in from Recent Sessions

From the dashboard's Recent Sessions list, click a session and land on a conversation reconstruction view for that session.

### Use-Case 2 — Deep-link by session id

Open a stable dashboard URL for any known session identifier (so skills can offer a link to peruse a whole prior conversation).

### Use-Case 3 — Export for richer tooling

Optionally download/export the reconstructed conversation as markdown or JSON when basic in-dashboard rendering is not enough.

## Requirements

1. Add a dashboard conversation-reconstruction view that shows a session's messages in order.
2. Wire the Recent Sessions list so clicking a session navigates into that view.
3. Support opening the view by any session identifier (deep-linkable URL suitable for skills to share).
4. Render message content as **basic markdown only** via a vendored JS markdown library (no CDN at runtime).
5. Do **not** enable markdown extensions (no Mermaid, footnotes, tables-of-contents, etc.); operators who need richer rendering use export.
6. Optional: provide a download/export control offering markdown and/or JSON.

Source of truth: [Session Inspection in Dashboard (#39)](https://github.com/Texarkanine/stockroom/issues/39), plus operator clarification on markdown scope.

## Constraints

1. Stay fully offline at runtime — vendor the markdown library the same way Chart.js is vendored; annotate REUSE ownership.
2. Read-only over the warehouse — no schema mutation or ingest from the dashboard path.
3. Preserve existing dashboard invariants (loopback server, non-migrating `open_current()`, no package-manager/build path for the front-end unless planning explicitly changes that).
4. Basic markdown only — no extension ecosystem.

## Acceptance Criteria

1. Clicking a Recent Sessions row opens the conversation reconstruction view for that session.
2. A URL that includes a session identifier loads the same view for any session present in the warehouse (and fails clearly when missing).
3. Message bodies render basic markdown (headings, lists, links, code fences, emphasis) without Mermaid/footnotes/other extensions.
4. Optional export downloads markdown and/or JSON of the reconstructed conversation.
5. Dashboard remains offline (no CDN fetch for the markdown library) and read-only.
