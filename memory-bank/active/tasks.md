# Task: Phase 2 · Milestone 2 — `sr-semantic` (pure vector search)

* Task ID: `p2-embeddings-search` (sub-run m2)
* Complexity: Level 2
* Type: simple enhancement (new read surface)

Add a pure **vector-search** read surface, `stockroom.semantic`, run via
`python -m stockroom.semantic "<question>"`. It embeds the query with m1's
`bge-small-en-v1.5` encoder (applying bge's asymmetric **query** instruction
prefix — the spike's measured +0.037 MRR win), runs **cosine KNN over the `0003`
HNSW index**, **dedups multi-chunk hits to one row per owner message** (the
"max-sim" obligation m1 deferred), joins the winners back to their `messages`
rows, and prints a ranked table — all **read-only** through the
`warehouse.open()` chokepoint. It mirrors the Phase-1 `sr-query` engine-module
shape (a single runnable module with a `run_*` library entry + a `con`/encoder
injection seam) and reuses `stockroom.embed`'s `Encoder`/`BgeEncoder`/`EMBED_*`
so no embedding logic is duplicated. The polished `/sr-semantic` skill wrapper +
per-harness invocation stay deferred to Phase 5 (the `sr-query` precedent).

## Test Plan (TDD)

### Behaviors to Verify

Torch-free unit + in-process-CLI tests (deterministic `FakeEncoder`, the
`migrated_con` / `warehouse_home` fixtures) — mirrors how `test_embed.py` covers
the embed pipeline without a subprocess CLI file:

- **Query embedding shape**: `embed_query("hi", enc)` → one `EMBED_DIM`-length vector.
- **Query prefix applied by default**: `embed_query("hi", spy)` → the encoder receives `QUERY_PREFIX + "hi"` (spy encoder captures its input); with `prefix=""` it receives the bare query.
- **KNN nearest-first**: seed 3 distinct single-chunk messages, embed them, search the exact text of one (with `query_prefix=""` so the fake's query vector equals the stored chunk's) → that message is rank 1, distance ≈ 0.
- **Ranks + distances ascending**: results carry `rank = 1..n` in nondecreasing `distance` order.
- **Owner dedup (max-sim)**: seed one long *multi-chunk* message plus shorter ones, embed → the multi-chunk message appears **exactly once** in results (its nearest chunk), never once per chunk.
- **Limit respected**: seed > `limit` embedded messages → `len(results) == limit`; a `limit` larger than the corpus returns all.
- **Owner join fields**: each hit carries `harness`, `session_id`, `message_id`, `role`, `text` from the joined `messages` row.
- **Empty states**: no warehouse embeddings (messages present, none embedded) and no `con` injected → empty result list, no error.
- **Read-only owns-connection path**: with no `con`, `run_semantic_search` opens via `warehouse.open(read_only=True)` and returns hits over a seeded warehouse (`warehouse_home`).
- **CLI happy path** (in-process, `encoder_factory=FakeEncoder`): seeded + embedded warehouse → exit 0, prints a ranked table containing the matched text preview.
- **CLI `-k/--limit`**: caps the printed rows.
- **CLI missing-warehouse friendly**: no warehouse → exit 1, stderr "run … ingest" hint, **encoder never constructed** (no torch on the friendly path).
- **(torch-gated, CI-skipped) real-model end-to-end**: `importorskip("torch")` — embed 3 real messages with `BgeEncoder`, search a paraphrase of one → that message ranks first. The lone torch edge; reuses m1's `BgeEncoder` (not re-testing the encoder itself).

### Edge Cases

- Empty / whitespace-only query → exit nonzero (or 2) with a message, warehouse never opened (mirrors `query`'s empty-SQL guard).
- `limit <= 0` → rejected with a clean message.
- Long query (> chunk window): embedded as a **single** query vector (queries are not chunked — chunking is a storage-grain concern); document the bge 512-token truncation as acceptable for m2.

### Test Infrastructure

- Framework: `pytest`, configured in `skills/sr-search/pyproject.toml` (`[tool.pytest.ini_options]`); run via `make test` / `make ci` from repo root.
- Test location: `skills/sr-search/tests/`.
- Conventions: one test module per engine module (`test_<module>.py`); torch-free core uses injected fakes + `migrated_con`; the lone real-model test is `pytest.importorskip("torch")`-gated; in-process CLI tests call `main(..., encoder_factory=FakeEncoder)` (the embed precedent) rather than a subprocess file.
- New test files: `tests/test_semantic.py`.
- Shared helper: promote `FakeEncoder` from `test_embed.py` into `conftest.py` (importable by both `test_embed` and `test_semantic`) — a small DRY refactor, deterministic SHA-256→384-vec, unchanged behavior.

## Implementation Plan

> Each step is **test-first**: (a) write/adjust the failing test(s), run them and watch them fail for the right reason; (b) implement to green. Dependency-ordered so no step backtracks.

1. **Shared `FakeEncoder` in `conftest.py`** (test-infra refactor; no product behavior).
   - (a) — n/a (pure refactor; re-run `test_embed.py` after to prove no regression).
   - Files: `tests/conftest.py` (add the `FakeEncoder` class, moved verbatim from `test_embed.py`), `tests/test_embed.py` (import it from conftest, drop the local copy).
   - Changes: move the deterministic encoder so both suites share one definition; `FakeEncoder._vector` stays a staticmethod (the KNN test uses it).

2. **`embed_query` + `QUERY_PREFIX`** (pure query-encoding seam, torch-free).
   - (a) tests: prefix-applied-by-default (spy encoder), `prefix=""` passthrough, one `EMBED_DIM` vector.
   - Files: `src/stockroom/semantic.py` (new), `tests/test_semantic.py` (new).
   - Changes: `QUERY_PREFIX = "Represent this sentence for searching relevant passages: "` (the documented bge-small-en-v1.5 query instruction); `embed_query(query: str, encoder: Encoder, *, prefix: str = QUERY_PREFIX) -> list[float]` returns `encoder.encode([prefix + query])[0]`. Import `Encoder`, `EMBED_DIM`, `EMBED_MODEL`, `BgeEncoder` from `stockroom.embed`.

3. **`SemanticHit` + `run_semantic_search`** (the KNN + dedup + owner-join core).
   - (a) tests: nearest-first, ranks/distances ascending, owner dedup, limit, owner-join fields, empty states, read-only owns-connection path.
   - Files: `src/stockroom/semantic.py`, `tests/test_semantic.py`.
   - Changes:
     - `@dataclass SemanticHit { rank: int; distance: float; harness: str; session_id: str; message_id: str; role: str; text: str }`.
     - `DEFAULT_LIMIT = 10`; `OVERFETCH = 10` (fetch `limit * OVERFETCH` chunk hits before dedup, so multi-chunk owners can't crowd out distinct owners).
     - `run_semantic_search(query, encoder, *, con=None, limit=DEFAULT_LIMIT, query_prefix=QUERY_PREFIX) -> list[SemanticHit]`: owns-connection via `warehouse.open(read_only=True)` when `con is None` (closed on return), mirroring `query.run_query`. Embeds the query (`embed_query`), runs the **index-accelerated KNN** `SELECT harness, owner_id, array_cosine_distance(vector, ?::FLOAT[384]) AS distance FROM embeddings WHERE owner_table = 'messages' ORDER BY distance LIMIT ?` (`limit * OVERFETCH`), dedups to the nearest chunk per `(harness, owner_id)` preserving ascending distance, truncates to `limit`, then a second query joins those owners to `messages` (`harness`, `session_id`, `message_id`, `role`, `text`) and assembles ranked `SemanticHit`s.

4. **CLI `main` + `_format_hits`** (the runnable surface).
   - (a) tests: CLI happy path (`encoder_factory=FakeEncoder`), `-k/--limit`, missing-warehouse friendly (encoder not built), empty/whitespace query guard, `limit <= 0` guard.
   - Files: `src/stockroom/semantic.py`, `tests/test_semantic.py`.
   - Changes: `_build_parser()` (positional `query`; `-k/--limit` int, default `DEFAULT_LIMIT`); `_format_hits(hits) -> str` renders a column-aligned ranked table (`rank | score | harness | role | preview`) where **`score` is cosine similarity = `1 - distance`** (rounded) — friendlier than raw distance for a search surface, computed at display time from the canonical `SemanticHit.distance` (no extra query cost); `text` is previewed to a fixed `PREVIEW_CHARS` width — a *display* preview only, **not** m3's context-aware read-time truncation (the no-truncation-at-rest invariant is untouched); `main(argv=None, *, encoder_factory=BgeEncoder) -> int` mirrors `embed.main`: validate args, friendly missing-warehouse check **before** building the encoder (keeps the friendly path torch-free), build via `encoder_factory`, run read-only, print, return `0`/`1`/`2`. `if __name__ == "__main__": raise SystemExit(main())`.
   - (a) add a test asserting the rendered table shows a `score` ≈ `1 - distance` (e.g. an exact-match hit with `query_prefix=""` shows `score` ≈ `1.0`).

5. **(torch-gated) real-model end-to-end** (the lone CI-skipped edge).
   - (a) test: `importorskip("torch")`; embed a few real messages with `BgeEncoder`, search a paraphrase → expected message ranks first.
   - Files: `tests/test_semantic.py`.
   - Changes: a single gated integration proving the prefix/asymmetric contract behaves end-to-end with the real model.

6. **Docs** (implementation work, not afterthought).
   - Files: `memory-bank/techContext.md`, `memory-bank/systemPatterns.md`, `skills/sr-search/SKILL.md`.
   - Changes: add a "Semantic search (`sr-semantic`)" section to `techContext.md` (module, KNN-over-HNSW, owner dedup, query prefix, read-only, deferred skill wrapper); extend the embeddings pattern in `systemPatterns.md` with the **over-fetch-then-max-sim-dedup** read pattern and the **asymmetric query-prefix** note; update `SKILL.md` engine status to mark `sr-semantic` built.

## Technology Validation

No new technology — validation not required. `sentence-transformers`/torch enter only via the **reused** `stockroom.embed.BgeEncoder` (already locked-out-of-lock + provisioned out of band, m1); `vss`/`array_cosine_distance` + the `0003` HNSW index already ship and are loaded at the chokepoint. No `uv.lock` change expected.

## Dependencies

- m1 (complete): `stockroom.embed` (`Encoder`, `BgeEncoder`, `EMBED_MODEL`, `EMBED_DIM`), the `0003` cosine HNSW index, and `warehouse.ensure_vss` on every connection.
- The `warehouse.open()` chokepoint (read-only path) and the `migrated_con` / `warehouse_home` fixtures.
- `array_cosine_distance` (DuckDB `vss`).

## Challenges & Mitigations

- **Owner dedup vs. HNSW top-k**: a `GROUP BY owner MIN(distance)` would dedup perfectly but defeat the index's top-n acceleration. *Mitigation*: keep the index-accelerated `ORDER BY distance LIMIT (limit*OVERFETCH)`, then dedup in Python — uses the index *and* dedups; `OVERFETCH=10` makes it vanishingly unlikely a distinct owner is starved by a multi-chunk neighbor at m2 corpus sizes. If this proved insufficient it'd be a tuning change, not a re-architecture.
- **`WHERE owner_table='messages'` + HNSW**: a filter alongside the KNN top-k *could* reduce index use. *Mitigation*: m1 embeds messages-only, so the filter currently matches every row (correctness is unaffected either way); keep it for forward-correctness when `tool_calls` embeddings land, and note the interaction.
- **Query-prefix testability**: bge's asymmetric prefix means a real query vector lands *near* (not equal to) a no-prefix passage vector, but `FakeEncoder` has no such geometry. *Mitigation*: thread `query_prefix` through `run_semantic_search`; correctness tests pass `query_prefix=""` (exact fake match), a dedicated spy test asserts the default prefix is applied, and the real asymmetric behavior is covered by the torch-gated test.
- **Display preview vs. the no-truncation invariant**: m2 must not flood the caller with a 200 KB message, but read-time truncation is m3's headline feature. *Mitigation*: a fixed-width *display* preview only (full text stays in the store and in the returned `SemanticHit.text`); the context-aware truncation levels are explicitly left to m3.
- **Re-level guard**: none of the above introduces a new component or an open design question (the prefix and per-chunk/dedup grain were settled by the m1 spike + creative docs). If dedup or index ergonomics unexpectedly demand a design decision, STOP and re-level to L3 — not expected.

## Preflight Findings (2026-06-29)

PASS. Validated against codebase reality; no blocking findings.

- **[folded in] Relevance score column.** `_format_hits` now displays cosine *similarity* (`1 - distance`) rather than raw distance — friendlier for a search surface, display-only, no query-cost (Step 4 amended).
- **[advisory · not changed] Optional `--harness` filter.** The cross-milestone invariant frames per-harness search as "by filtering the `harness` column." m2 satisfies "cross-harness by default" simply by *not* filtering; adding an optional `--harness cursor|claude` arg is the natural completion of that invariant but is deferred — it fits more naturally with m3's user-facing routing surface, and adding it now would be mild scope creep on a "pure vector search" engine module (the `sr-query` precedent shipped raw and deferred polish to Phase 5). Revisit in m3.
- **[advisory · not changed] `_format_hits` vs `query._format_table` duplication.** Both render column-aligned text tables. They are *not* merged now: `query._format_table` is private and renders generic columns/rows, while `_format_hits` has search-specific shape (rank/score/preview). If m3 needs a third tabular renderer, extract a shared helper then — premature now (YAGNI).

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [ ] Preflight
- [ ] Build
- [ ] QA
