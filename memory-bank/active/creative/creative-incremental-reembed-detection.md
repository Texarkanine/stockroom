# Algorithm/Architecture Decision: Incremental Re-embed — New & Changed Detection

## Requirements & Constraints

Ranked attributes:

1. **Correctness of "incremental"** — the "Done When" demands new content re-embeds incrementally, **not from scratch**. Re-embedding the whole corpus every run is the explicit anti-goal (embeddings are the expensive asset).
2. **Changed-content honesty** — m1's charter is "un-embedded **or changed** content." A message whose text changed must not keep a stale vector forever.
3. **Minimal blast radius** — embeddings are derived data; the mechanism should not require a new schema column or a full-table rebuild if a cheaper principled option exists.

Constraints from existing code:
- `message_id = '{session_id}#{ordinal}'` is **stable across re-ingest** — an edited message keeps its id, so "row missing" cannot detect an edit.
- Ingest is **delete-then-insert per `(harness, session_id)`** (`stockroom.ingest.writer`); it currently does **not** touch `embeddings`.
- `embeddings.embed_model` is recorded; there is no content hash / updated_at on `embeddings`.

## Options Evaluated

- **Option A — new-only (current-model) selection**: embed every owner that has **no `embeddings` row for the current `embed_model`**. A `LEFT JOIN embeddings … AND embed_model = ?` / `NOT EXISTS` query. Covers new content *and* a model change; does **not** detect an edit to an already-embedded message.
- **Option B — cascade-invalidate on re-ingest**: the ingest writer deletes a session's `embeddings` in the same delete-then-insert it already does per `(harness, session_id)`, so re-ingested (hence possibly changed) content is naturally re-embedded on the next embed run. Pairs with A.
- **Option C — content-hash column**: add `embeddings.source_hash` via `0003`; re-embed when the stored hash differs from the live row's hash. Most precise per-row change detection.

## Analysis

| Criterion | A (new-only) | A+B (cascade) | C (hash column) |
|-----------|-------------|----------------|-----------------|
| New content incremental | ✓ | ✓ | ✓ |
| Detects edits | ✗ | ✓ (session re-ingested ⇒ embeddings dropped ⇒ re-embedded) | ✓ (finest grain) |
| Schema surface added | none | none | new column + hashing on every row |
| Blast radius | embed module only | embed module + ~2 lines in `ingest.writer` (tested) | `0003` + writer + embed selection |
| Principle | — | derived data invalidated with its source (clean) | precise but heavier |

Key insights:
- Edits only ever arrive **through re-ingest** (the warehouse is ETL output; nothing else mutates `messages`). Re-ingest already deletes-and-reinserts the whole session. So invalidating that session's embeddings in the *same* operation is the natural, principled way to catch edits — embeddings are derived from messages and should not outlive the rows they describe.
- Option C's per-row precision buys nothing over A+B here, because re-ingest is already session-grained delete-then-insert; a hash column adds schema surface and per-row hashing cost to detect a change that B catches for free at the exact moment it can occur.
- A alone is insufficient for the "changed" half of the charter; A+B together satisfy both halves with no schema change.

## Decision

**Selected**: **A + B** — new-only current-model selection for the incremental engine, plus session-grained embedding cascade-delete in the ingest writer.

**Rationale**: Satisfies both halves of the charter (new *and* changed) with **zero schema change**, using the principled rule that derived embeddings are invalidated together with the source session they describe. The incremental selection (A) is the m1 headline; the cascade (B) is a ~2-line, well-localized, tested addition to the one place that already rewrites sessions.

**Tradeoff**: m1 touches `stockroom.ingest.writer` (Phase-1 code) — a small, deliberate widening. Accepted: the change is minimal, principled, and directly tested; the alternative (hash column) is heavier and adds permanent schema surface.

## Implementation Notes

- **Selection (A)** — `embed_pending(con, encoder, *, embed_model)` selects owners needing a vector:
  `SELECT m.harness, m.session_id, m.message_id, m.text FROM messages m WHERE m.text IS NOT NULL AND length(trim(m.text)) > 0 AND NOT EXISTS (SELECT 1 FROM embeddings e WHERE e.harness = m.harness AND e.owner_table = 'messages' AND e.owner_id = m.message_id AND e.embed_model = ?)`.
- **Cascade (B)** — in `ingest.writer`, wherever a session's `messages`/`tool_calls` are deleted before re-insert, also `DELETE FROM embeddings WHERE harness = ? AND owner_table IN ('messages','tool_calls') AND owner_id IN (SELECT message_id FROM messages WHERE harness=? AND session_id=?)` — or, equivalently and more simply, delete embeddings for the session's owner rows before the rows themselves are deleted. Exact form pinned test-first in `test_ingest_writer.py`.
- Deletes run against the **live HNSW index** (experimental persistence enabled by the chokepoint) — spike-verified to work.
