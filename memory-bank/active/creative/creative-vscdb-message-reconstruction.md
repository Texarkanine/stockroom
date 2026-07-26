# Algorithm Decision: vscdb bubble → warehouse message reconstruction

## Problem

Turn one Cursor composer's ordered bubble list into `NormalizedMessage` rows.

**Input.** `composerData:{id}.fullConversationHeadersOnly` — an ordered `[{bubbleId, type}, …]` list (present for 609 of the 908 backfill candidates; 26 older composers instead carry whole bubbles inline in a legacy `conversation[]` array; 273 have neither and are empty drafts). Each referenced `bubbleId:{composerId}:{bubbleId}` row is a JSON bubble with `type` (1 = user, 2 = assistant), `text`, optional `toolFormerData` (one tool call: `name`, `toolCallId`, `rawArgs`/`params`, `status`, `result`), optional `thinking`, `tokenCount`, and usually an ISO-8601 `createdAt`.

**Output.** Dense 0-based `ordinal` messages in conversation order with a linear `parent_ordinal` chain, each carrying text, tool calls, and (where available) `ts`.

**Volume.** ~75,800 bubbles across the 908 candidates; 207,926 bubbles DB-wide, of which 167,126 (80%) carry storable content and 40,800 (20%) are thinking-only or wholly empty.

**Invariants.** Thinking is never stored. Tool *results* are never stored; tool *inputs* are stored whole. Ordinals are dense over kept messages. No fabricated content.

A real 27-bubble conversation illustrates the shape — tool calls arrive as their own bubbles, not as blocks inside the assistant's text bubble:

```
 0 t=1 text          "I'm trying to build a Windows batch script…"
 1 t=2 text          "Let me help you evaluate the options…"
 2 t=1 text          "Okay, I want to extract the Configuration.Other…"
 3 t=2 text          "I'll help you create a PowerShell script…"
 4 t=2 tool:edit_file  (text empty)
 5 t=2 text          "Now I'll create a batch file wrapper…"
 6 t=2 tool:edit_file  (text empty)
 …
```

## Options Evaluated

- **Option A — one bubble, one message**: every referenced bubble becomes a message, including thinking-only and empty ones.
- **Option B — storable bubbles only**: a bubble becomes a message when it has non-empty text or a tool call; thinking-only and empty bubbles are consumed and dropped.
- **Option C — merge tool bubbles into the preceding assistant turn**: reproduce the agent-transcripts `[text, tool_use, …]` turn shape by folding each tool bubble into the assistant message before it.

## Analysis

| Criterion | A (one-for-one) | B (storable only) | C (merge into turns) |
|---|---|---|---|
| Correctness | Faithful; but emits rows with nothing in them | Faithful; drops only bubbles whose entire content is unstorable by contract | Invents turn grouping the source does not record (`grouping` is `null` on every header sampled) |
| Simplicity | Simplest | One predicate more than A | Lookback state machine + synthetic block indices + orphan-tool edge cases |
| Reuse | Mirrors `cursor_chats._parse_messages` | Mirrors `cursor_chats._parse_messages` plus a filter | No existing analog to reuse |
| Maintainability | High | High | Lowest — the merge rule is a judgement call every future reader must re-derive |
| Time | O(n) | O(n) | O(n) |
| Space | O(n) | O(n) ≈ 0.8·A | O(n) |
| Rows produced (DB-wide) | 207,926 | 167,126 | ~110,000 (est.) |

Key insights:

- **Dropping thinking-only bubbles loses nothing that would have been stored.** Because `thinking` is never persisted, a thinking-only bubble under Option A becomes a message whose every column is empty — a row that costs storage and dilutes message counts while carrying zero recoverable information. That makes B strictly better than A rather than a fidelity trade.
- **Option C's fidelity gain is an illusion.** It would make vscdb rows resemble agent-transcripts rows, but the resemblance is manufactured: the source records no turn grouping, so the merge boundary would be our invention. It also has genuinely ambiguous cases — a tool bubble that opens a conversation, or follows a user bubble, has no assistant turn to merge into — and it destroys the per-bubble `createdAt` and `tokenCount` alignment that B preserves for free.
- **Per-bubble `createdAt` is a bonus this source offers.** 175,781 bubbles carry an ISO-8601 timestamp, so vscdb-sourced messages can populate `messages.ts` (and therefore session `started_at`/`ended_at`) — a grain the agent-transcripts parser cannot fill at all. The schema's column meaning is harness-independent, so filling it is honest extraction, not a contract violation.
- **The legacy inline `conversation[]` array is the same bubble shape, just embedded.** Supporting it is a different *source of the bubble objects*, not a different reconstruction algorithm — so all 26 of those composers come along for a few lines of code.

## Decision

**Selected**: Option B — storable bubbles only.

**Rationale**: It is the simplest mapping that stores everything the schema is willing to store, it reuses the established `cursor_chats` walk-and-keep structure, and it avoids inventing conversational structure that the source does not record. The 20% of bubbles it drops are precisely those whose content the warehouse contract forbids storing, so nothing recoverable is lost.

**Tradeoff**: vscdb-sourced sessions will show tool calls as their own assistant messages rather than as blocks attached to a text turn, so their message counts run higher than an agent-transcripts session of comparable length. Accepted: the alternative buys cosmetic comparability with fabricated grouping.

## Implementation Notes

- **Kept predicate**: keep a bubble when `text` is non-empty after strip, or `toolFormerData` is present. Consume everything else (thinking-only, empty, missing bubble rows, unknown `type`) without emitting a row.
- **Role**: `type == 1` → `user`, `type == 2` → `assistant`; any other value is not a message and is skipped.
- **Text**: store the bubble's `text` verbatim (whole, untruncated). `thinking` is never read into `text`.
- **Tool calls**: one per bubble at most. `tool_name` = `toolFormerData.name`; `source_tool_use_id` = `toolCallId`; `tool_input` = parsed `rawArgs` JSON, falling back to `params`, and to the raw string when neither parses (stored whole either way). `toolFormerData.result` is never stored. `ordinal` = 1 when the bubble also has text (mirroring `[text, tool_use]`), else 0.
- **Ordering**: `fullConversationHeadersOnly` order; fall back to the legacy inline `conversation[]` array when headers are absent; a composer with neither yields no messages and is skipped entirely (D4).
- **Missing bubbles**: a header referencing a `bubbleId` row that does not exist is skipped — this is normal (Cursor prunes bubbles) and must not abort the composer.
- **Timestamps**: parse bubble `createdAt` (ISO-8601, `Z`-suffixed) into naive UTC via `stockroom.timestamps`; leave `ts` NULL when absent or unparseable. Session `started_at`/`ended_at` = min/max of parsed message timestamps, falling back to `composerData.createdAt` (epoch ms) for `started_at`.
- **Tokens**: attach a bubble's allowlisted `tokenCount.inputTokens` / `outputTokens` to *that bubble's own message* when nonzero, leaving both `None` otherwise; session-grain `*_tokens` stay NULL and `session_token_usage` rolls the messages up. Kept bubbles are the only ones that matter: a probe of 120 composers / 14,446 bubbles found 100% of nonzero counts on storable bubbles and **none** on the thinking-only and empty bubbles this algorithm drops. (Supersedes this note's original session-Σ, which was carried over from the aborted enrich design; see D6 in `tasks.md`.)
