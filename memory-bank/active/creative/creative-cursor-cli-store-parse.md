# Algorithm Decision: Cursor CLI store.db Parse

## Problem

Reconstruct a harness-neutral `NormalizedSession` from a Cursor Agent CLI chat at `~/.cursor/chats/<hash>/<agentId>/store.db`.

**Input:** SQLite DB with `meta` (hex-JSON: `agentId`, `latestRootBlobId`, `name`, `mode`, `createdAt`, optional `lastUsedModel`) and `blobs(id TEXT PK, data BLOB)` where leaves are mixed JSON role messages and opaque/protobuf nodes.

**Output:** Ordered kept `user`/`assistant` messages with text + tool **inputs** only; session fields (`session_id`, `title`, `entrypoint='cli'`, optional `cwd`/`started_at`); no tool results; no reasoning/thinking text.

**Invariants:**
- Dense ordinals over kept turns; linear `parent_ordinal`
- Faithful capture of kept text and tool inputs (no truncation)
- Drop `system`, `tool` (tool-result), and `reasoning` content parts (existing Cursor/Claude contracts)
- Conversation order must match the CLI’s own root chain, not an arbitrary blob iteration order

## Options Evaluated

- **A — Ordered root-hash walk:** Parse `latestRootBlobId` blob as repeated protobuf length-delimited 32-byte refs (field tag 10); that sequence is conversation order; decode JSON leaves only.
- **B — Unordered JSON collect:** Load every JSON `user`/`assistant` blob; invent order (mtime, id sort, etc.).
- **C — Prefer agent-transcript for order:** When a same-id transcript exists, take order/text from JSONL and tools from store (or skip store).
- **D — Full blob-graph BFS/DFS:** Walk all hash edges from root recursively for a total order.

## Analysis

| Criterion | A Root-hash walk | B Unordered JSON | C Transcript-first | D Full graph walk |
|-----------|------------------|------------------|--------------------|-------------------|
| Correctness | Matches CLI root order (verified on collision sample) | Ordinals wrong / unstable | Only when transcript exists (86/87 chats have none) | Redundant; root already linear |
| Simplicity | Small protobuf bytes-field scan + JSON leaf decode | Simplest code, wrong product | Two sources, merge rules | More code, same order as A |
| Reuse | Fits `NormalizedSession` / writer unchanged | Same | Couples CLI to IDE layout | Same as A |
| Maintainability | Clean-room, localized | Fragile | Dual-path forever | Harder without benefit |

Key insights:
- The root blob is already a linear list of 32-byte blob ids (`0a 20 <sha256>…`); no deep graph walk needed for order.
- Assistant JSON leaves use `type: "tool-call"` with `toolName` / `args` (map to existing tool_use → `NormalizedToolCall`).
- Opaque/`tool` blobs are tool-results or internals — ignore for warehouse rows (inputs live on assistant turns).

## Decision

**Selected**: Option A — Ordered root-hash walk

**Rationale**: Only approach that yields correct order for chats-only sessions (the common case) without inventing sort keys, while staying a single-source clean-room parser aligned with existing ingest contracts.

**Tradeoff**: Depends on Cursor keeping the root as a flat hash list. Production parsing fails soft (empty / partial order, or skip the session on sqlite errors) so ingest continues; tests against fixture `store.db`s fail loudly to expose drift. We do not parse arbitrary protobuf schemas beyond “repeated 32-byte length-delimited fields.”

## Implementation Notes

- `session_id` / `agent_id` = directory name (= `meta.agentId`)
- `title` = `meta.name` when present
- `entrypoint` = `'cli'` (stamped by parser or orchestrator from provenance)
- `started_at` = `createdAt` ms → naive UTC (honest grain available for CLI; IDE Cursor remains None)
- `cwd`: best-effort from first `user_info` / `Workspace Path:` in a user blob; `project_id` = parent hash dir name (verbatim)
- `models`: optional `[lastUsedModel]` when meta has it
- Skip non-JSON / non-user-assistant leaves in the root chain
- Map content parts: `text` kept; `tool-call` → tool call; `reasoning` dropped
- Unit-test with a trimmed fixture copied from a real `store.db` (or synthesized blobs + meta)
