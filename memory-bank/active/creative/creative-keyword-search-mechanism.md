# Architecture Decision: Keyword-Search Mechanism for `sr-search`

## Requirements & Constraints

`sr-search` needs a **keyword** result set to blend with the semantic one. The keyword
half must match literal terms over the **untruncated stored `messages.text`** (the
tech-brief: "keyword matching runs over the untruncated stored content").

Quality attributes, ranked for this decision:

1. **Alignment with the offline / supply-chain posture** — a tool that reads every
   conversation must not pull un-audited code at runtime. New network `INSTALL`s are a
   cost, not free.
2. **Correctness over live, incremental data** — the warehouse changes on every ingest;
   a keyword result must reflect current content with no rebuild step.
3. **Simplicity (read-only surface)** — `sr-search` opens `read_only=True`; it must not
   need to create or maintain any stored artifact.
4. **Ranking quality** — a relevance signal from the keyword side is *nice to have* for
   fusion, but secondary to the three above at m2/m3 corpus scale.

Technical constraints: DuckDB 1.5.4; read-only chokepoint; m1/m2 already pay the `vss`
install cost; clean-room boundary.

Out of scope: regex search surfaces, multi-term boolean query languages, stemming/locale
tuning — all YAGNI for v1.

## Components

The keyword path is one query inside `run_search`, against the existing `messages` table
through the same connection the semantic path uses. The decision is purely *which query
mechanism*; no new component or boundary is introduced either way.

## Options Evaluated

- **Option A — DuckDB FTS (`PRAGMA create_fts_index` + `match_bm25`)**: a real
  inverted-index full-text search with BM25 relevance scoring and tokenization.
- **Option B — `ILIKE` substring scan**: `WHERE text ILIKE '%term%'` over the stored
  text, no index, no extension.

## Analysis

Probe findings (DuckDB 1.5.4, run against an in-memory DB in the engine env):

| Criterion | A — FTS / BM25 | B — `ILIKE` |
|-----------|----------------|-------------|
| Offline posture | ✗ un-bundled — `LOAD fts` fails, needs a network `INSTALL fts` | ✓ built-in, zero extensions |
| Incremental correctness | ✗ `create_fts_index` index is **stale after insert** (probe: a new matching row did not appear without a rebuild) — every ingest must drop+rebuild it | ✓ always reflects current `text` |
| Read-only surface | ✗ `create_fts_index` materializes a stored `fts_main_messages` schema — a **write/DDL**; can't be created by a RO connection, so it'd need a migration or an embed/ingest-time build step | ✓ pure read, nothing to materialize |
| Simplicity | ✗ extension + index lifecycle + rebuild hook + migration/snapshot churn | ✓ one `WHERE` clause |
| Ranking | ✓ BM25 relevance score | ✗ boolean match only (no keyword-side rank) |
| Time complexity | sub-linear via inverted index | O(n) scan per query |

Key insights:

- **The decisive factors are posture + incrementality, not raw search quality.** FTS
  drags in the same network-`INSTALL` tension as `vss` *plus* a stored, non-auto-updating
  index that contradicts both the read-only surface and the incremental-data model. That
  is a large, ongoing lifecycle cost (a rebuild hook wired into ingest, a new migration +
  golden-snapshot, staleness as a correctness bug) for a secondary benefit.
- **The lost benefit (keyword ranking) is cheaply recovered downstream.** Fusion does not
  need a keyword *score*: rank-based fusion (RRF) ranks the keyword set by a stable,
  free ordering signal already in the schema (recency / `ordinal`), and lets the
  semantic side carry the relevance weight. So Option B's one weakness is absorbed by the
  fusion design rather than being a true gap. (Resolved in
  `creative-search-routing-and-fusion.md`.)
- **The tech-brief already steers here**: it specifies keyword matching as "SQL
  `ILIKE`-style", and the corpus scale is the same one m2's semantic over-fetch scans
  linearly without issue.

## Decision

**Selected**: Option B — `ILIKE` substring scan over `messages.text`.

**Rationale**: It is the only option that honors the top-three ranked attributes (offline
posture, incremental correctness, read-only simplicity) without contortion. FTS optimizes
the lowest-ranked attribute (keyword ranking) at the direct expense of all three higher
ones, and its stored-index staleness is a latent correctness bug against live ingest.

**Tradeoff**: No keyword-side relevance score and an O(n) scan per query. Both are
acceptable: ranking is delegated to RRF over a free ordering signal, and a linear scan
over the message corpus is the same order of work m2's semantic path already does. If a
future phase proves keyword ranking is genuinely needed at scale, FTS can be revisited as
an ingest-time-built, migration-backed index — a deliberate later optimization, not a v1
requirement.

## Implementation Notes

- Keyword query: case-insensitive `ILIKE` on `messages.text`, parameterized
  (`text ILIKE '%' || ? || '%'`) — never string-interpolated. Multi-word handling stays
  simple for v1: treat the whole query string as one `ILIKE` term (a phrase contains
  match). Tokenized AND/OR is YAGNI; revisit only if a real need appears.
- Order the keyword set deterministically for stable fusion input (e.g. most-recent
  first via `ts`/`ordinal`, then `message_id`); the exact ordering signal is fixed in the
  routing-and-fusion doc.
- Bound the keyword set the same way semantic over-fetches: fetch up to `limit * OVERFETCH`
  (or a keyword-specific cap) so fusion has candidates without an unbounded scan result.
- Reuse the `WHERE owner-grain`/owner-join shape already proven in `semantic.py`; the
  keyword path joins nothing extra (it queries `messages` directly).
