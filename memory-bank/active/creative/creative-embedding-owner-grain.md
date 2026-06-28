# Architecture Decision: Embedding Owner Grain (what gets embedded)

## Requirements & Constraints

Ranked quality attributes:

1. **Headline fitness** — Phase 2 exists to make conversation content "findable by meaning." Semantic search over message text is the deliverable that m2 (`sr-semantic`) and m3 (`sr-search`) consume.
2. **One-meaning-per-field / no ambiguous keys** — the `embeddings` PK is `(harness, owner_table, owner_id, chunk_index)`. `owner_id` must deterministically identify exactly one owner row.
3. **Scope containment** — m1 is L3; avoid pulling in low-signal surface that widens the milestone.
4. **Forward-compatibility** — a later milestone must be able to add a second owner kind without a migration.

Constraints from the schema (`0001`):
- `messages` PK is `(harness, session_id, message_id)`; `message_id = '{session_id}#{ordinal}'` is the uniform identity. Clean single key.
- `tool_calls` PK is `(harness, session_id, message_id, ordinal)` — `message_id` **alone is ambiguous** (multiple tool calls per turn).
- `embeddings.owner_table` is `'messages' | 'tool_calls'` — the table already anticipates both kinds.
- Chunk-and-mean-pool yields **one vector per owner** (tech brief), i.e. `chunk_index = 0`.

## Components

The embed selection query (which owner rows need a vector) and the writer (what `owner_table`/`owner_id` it stamps). No new tables.

## Options Evaluated

- **Option A — messages only (v1)**: `owner_table='messages'`, `owner_id=message_id`, `chunk_index=0`, embedding `messages.text`. Sidesteps the `tool_calls` ambiguity entirely; covers the headline.
- **Option B — messages + tool_calls**: also embed `tool_calls.tool_input` with a composite `owner_id = '{message_id}#{ordinal}'`. Broader coverage.

## Analysis

Two options, prose comparison:

- **Headline fitness**: Both satisfy it; A satisfies it fully on its own (message text *is* the conversation). B adds tool-input search, which is lower-signal: `tool_input` is irreducibly heterogeneous JSON (per the schema's JSON-only-for-heterogeneity pattern), and mean-pooling an embedding of a JSON blob is a crude signal compared to natural-language message text.
- **Key ambiguity**: A uses the clean `message_id`. B must invent a composite `owner_id` convention (`{message_id}#{ordinal}`) — workable and PK-safe, but a new convention to define, test, and carry.
- **Scope/risk**: A is strictly smaller and lower-risk for an L3 milestone. B widens m1 and front-loads a decision (is tool-input semantic search even wanted?) that no milestone currently depends on.
- **Forward-compatibility**: A loses nothing — `owner_table` already supports adding `'tool_calls'` later as a purely additive change (new rows, no migration, no rework of message embeddings).

Key insight: the schema was deliberately built to *allow* both grains precisely so the choice could be deferred; choosing messages-only now is the reversible, low-risk default, and the expensive/ambiguous half can be added later if a real need appears.

## Decision

**Selected**: Option A — **messages only for m1**.

**Rationale**: It fully delivers the headline (semantic search over conversation text) using the clean, unambiguous `message_id` key, keeps the L3 milestone contained, and sacrifices nothing structurally — `owner_table` already supports adding `'tool_calls'` later as an additive change.

**Tradeoff**: Tool-input semantic search is not available in v1. Accepted and explicitly deferred; revisit only if a concrete need surfaces (it would define the `{message_id}#{ordinal}` composite key at that point).

## Implementation Notes

- Embed `messages` rows where `text IS NOT NULL AND length(trim(text)) > 0` (empty/whitespace turns produce no vector).
- Write one row per message: `(harness, 'messages', message_id, 0, embed_model, vector)`.
- Selection and writer must be written so adding `tool_calls` later is additive (don't hardcode assumptions that there is only ever one `owner_table`).
