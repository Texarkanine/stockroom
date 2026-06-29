# Task: Phase 2 · Milestone 3 — `sr-search` (blended keyword + semantic search)

* Task ID: `p2-embeddings-search` (L4 sub-run m3)
* Complexity: Level 3
* Type: feature (new read surface composing m1 embedder + m2 semantic search + a new keyword path)

The friendly default search entrypoint. Run keyword search and semantic search over the
warehouse, **merge and rank** the two result sets (RRF), and apply a context-aware
**read-time truncation** level so retrieving a huge field never floods the caller's
context window. Engine module `stockroom.search` (`python -m stockroom.search`), following
the Phase-1 `query` / m2 `semantic` engine-module precedent; the polished `/sr-search`
skill wrapper + per-harness invocation stay deferred to Phase 5.

## Pinned Info

### Search data flow (routing → fusion → read-time truncation)

Pinned because the whole milestone is this one pipeline; every step and test maps onto it.

```mermaid
flowchart LR
    Q["query (+ mode, harness, -k, --detail)"] --> R{mode}
    R -->|keyword| KW["keyword set\nILIKE over messages.text\n(no torch)"]
    R -->|semantic| SEM["semantic set\nrun_semantic_search (reuse m2)"]
    R -->|blend (default)| KW
    R -->|blend (default)| SEM
    KW --> F["fuse(): RRF by (harness, message_id)\nvia ∈ keyword|semantic|both"]
    SEM --> F
    F --> H["SearchHit list — FULL text (no trim at rest)"]
    H --> T["_format_hits: _truncate(text, detail)\ncompact | snippet (default) | full"]
    T --> OUT["ranked table"]
```

## Component Analysis

### Affected Components

- **`stockroom.search` (NEW)** — the deliverable. Read-only surface: keyword query +
  semantic query → RRF fuse → render with a detail-level truncation. Mirrors the
  `query.py`/`semantic.py` shape (`run_*` library entry + `con`/encoder injection + `main`
  + `_build_parser` + `_format_*`).
- **`stockroom.semantic` (REUSE, one additive change)** — `run_semantic_search(...)` is the
  semantic half. Gains an optional `harness: str | None = None` filter applied **inside**
  the embeddings KNN (so the top-k is correct, not post-filtered). Backward-compatible
  (default `None` = today's behavior).
- **`stockroom.embed` (REUSE, unchanged)** — `Encoder`/`BgeEncoder`/`EMBED_*`, reached via
  `semantic` and the CLI `encoder_factory` default.
- **`stockroom.warehouse` (REUSE, unchanged)** — `open(read_only=True)` chokepoint;
  `sr-search` is a pure reader.
- **`messages` table (READ)** — keyword `ILIKE` over untruncated `text`; owner-join columns
  (`harness`,`session_id`,`message_id`,`role`,`text`) + ordering signals (`ts`,`ordinal`)
  already exist (`0001`).
- **Docs** — `SKILL.md`, `techContext.md`, `systemPatterns.md`.

### Cross-Module Dependencies

- `search.run_search` → `semantic.run_semantic_search` (semantic set, sharing the same `con`).
- `search.run_search` → warehouse `messages` `ILIKE` (keyword set, same `con`); opens RO when `con is None`.
- `search` → `embed` only via `semantic` + the CLI default `encoder_factory=BgeEncoder`. Torch-free seam preserved by injecting `FakeEncoder` (the `test_semantic` precedent); keyword-only mode needs **no** encoder at all.

### Boundary Changes

- **No schema/migration change** — keyword is `ILIKE`; no FTS index, no `000N`, no snapshot churn (`creative-keyword-search-mechanism.md`).
- **New public surface** — `python -m stockroom.search` + `run_search(...)` returning a new `SearchHit` dataclass.
- **One additive m2 signature change** — `run_semantic_search(..., harness=None)`. No existing call sites break.

### Invariants & Constraints (binding)

1. **No truncation at rest** — truncation is read-time only and is this milestone's headline feature; full text stays whole in the store **and** in `SearchHit.text`; only the *rendered* output is trimmed.
2. **Read-only through the chokepoint** — `read_only=True`; DuckDB enforces immutability.
3. **Harness-labeled, cross-harness by default** — default omits `harness`; `--harness` narrows to one (the per-harness "filter" m2 deferred here).
4. **Clean-room boundary** — routing/fusion/truncation from briefs + first principles.
5. **Torch-safe + test-first + green `make ci`** — torch-free unit core vs `FakeEncoder`; real-model edge `importorskip("torch")`-gated; `--no-sync` local gate.

## Open Questions

- [x] **Keyword-search mechanism** → Resolved: **`ILIKE` substring** over `messages.text` (not FTS). Probe-backed: FTS is un-bundled (network `INSTALL`), and `create_fts_index` materializes a stored, **stale-on-insert** index — a write that clashes with the read-only surface + incremental model. See `creative-keyword-search-mechanism.md`.
- [x] **Query routing + rank fusion** → Resolved: **blend by default** + `--mode {blend,keyword,semantic}` (no auto-router; `sr-search` *is* the blend, pure surfaces are the escape hatches); fused with **Reciprocal Rank Fusion** (rank-based, fits the unranked keyword set, rewards dual-method hits). "SQL" routing collapses to the keyword path — **not** NL→SQL (out of scope). See `creative-search-routing-and-fusion.md`.
- [x] **Context-aware read-time truncation** → Resolved: **discrete detail levels** `compact|snippet|full`, default `snippet`, per-result char cap with a visible trim marker; trimming lives only in the render path. Total-output `--budget` is a noted future enhancement (YAGNI for v1). See `creative-read-time-truncation.md`.

## Test Plan (TDD)

### Behaviors to Verify

**m2 extension — `run_semantic_search` harness filter (`test_semantic.py`):**
- harness filter restricts hits → only the matching-harness owner is returned; default (`None`) is unchanged (cross-harness).

**Keyword search — `run_keyword_search` (`test_search.py`):**
- substring present in `text` → hit; absent → excluded.
- mixed case query/text → matched (`ILIKE` case-insensitive).
- multiple matches → ordered recency-first deterministically (`ts` desc NULLS LAST, `ordinal` desc, `message_id`).
- `harness=` set → only that harness; `limit` caps the keyword set.

**RRF fusion — `fuse()` (pure, no DB):**
- key in **both** lists outranks a key in only one (dual-method boost).
- fusing a single non-empty list preserves that list's order.
- result truncated to `limit`; `via` ∈ {keyword,semantic,both} reflects membership.
- deterministic tiebreak (equal RRF score → stable order).

**`run_search` orchestration (`test_search.py`, `migrated_con`/`warehouse_home`):**
- blend: a keyword-only match **and** a semantic-only match both appear.
- a message matching the query both literally and semantically ranks first.
- `mode="keyword"` runs no semantic (works with `encoder=None`); `mode="semantic"` runs no keyword.
- `harness=` filters both halves; `limit` caps results; empty corpus → `[]`.
- **no-truncation-at-rest**: a >SNIPPET_CHARS message → `SearchHit.text` holds the **whole** text.
- owns-connection path opens read-only (no `con`) and returns hits.

**Truncation + formatting (`_truncate`, `_format_hits`):**
- `compact` → single line ≤ cap; `snippet` → capped with a visible marker; `full` → verbatim; `None`/empty → `""`.
- rendered table: default `snippet` trims; `full` shows whole text; shows `via` + `score` columns; empty → `(0 results)` trailer.

**CLI `main` (in-process, `encoder_factory=FakeEncoder` / `_never_built`):**
- prints ranked results; `--mode keyword` works with `_never_built` (no torch built); `--detail full` shows whole text; `--harness` narrows.
- missing warehouse → exit 1 + "run ingest" hint, encoder never built; empty query → exit 2; non-positive `-k` → exit 2; invalid `--mode`/`--detail` → argparse exit 2.

**Real-model end-to-end (torch-gated, `importorskip("torch")`):**
- blend with `BgeEncoder`: a paraphrase query ranks its semantically-matching message first.

### Test Infrastructure

- Framework: `pytest` (configured in `skills/sr-search/pyproject.toml`); run via `make test` / the `--no-sync` gate.
- Test location: `skills/sr-search/tests/`.
- Conventions: one test module per engine module; shared `FakeEncoder`/`SpyEncoder` from `conftest`; `migrated_con` (full chain + `ensure_vss`) and env-pointed `warehouse_home` fixtures; in-process CLI via `main(..., encoder_factory=...)` (no subprocess); torch edge `importorskip`-gated.
- New test files: `skills/sr-search/tests/test_search.py`. Modified: `skills/sr-search/tests/test_semantic.py` (one new harness-filter test).

### Integration Tests

- `run_search` over `migrated_con` is the cross-component integration (keyword SQL + reused semantic KNN + fusion + owner rows) under the deterministic fake.
- The torch-gated real-model blend is the end-to-end across `embed` → index → `semantic` → `search`.

## Implementation Plan

Ordered, test-first; each step = one TDD cycle (write failing tests → implement → green). Start with the fewest-dependency piece (the m2 param) and work outward.

1. **m2: optional harness filter on `run_semantic_search`**
    - Files: `src/stockroom/semantic.py`, `tests/test_semantic.py`
    - Changes: add `harness: str | None = None`; when set, add `AND harness = ?` to the embeddings KNN (and carry through the owner join). New test first; existing m2 tests stay green (regression).
    - Creative ref: `creative-search-routing-and-fusion.md` (Implementation Notes).
2. **Keyword search**
    - Files: `src/stockroom/search.py` (new), `tests/test_search.py` (new)
    - Changes: `run_keyword_search(query, *, con, limit, harness=None)` — parameterized `ILIKE`, recency-first deterministic order, `LIMIT` cap; module constants (`DEFAULT_LIMIT`, candidate cap).
    - Creative ref: `creative-keyword-search-mechanism.md`.
3. **RRF fusion**
    - Files: `src/stockroom/search.py`, `tests/test_search.py`
    - Changes: pure `fuse(keyword_keys, semantic_hits, *, k=RRF_K, limit)` → ranked `(key, score, via)`; `RRF_K=60` constant; deterministic tiebreak.
    - Creative ref: `creative-search-routing-and-fusion.md`.
4. **`run_search` orchestrator + `SearchHit`**
    - Files: `src/stockroom/search.py`, `tests/test_search.py`
    - Changes: `SearchHit` (rank, score, via, owner fields, **full** text); `run_search(query, encoder, *, con=None, limit=, mode="blend", harness=None, query_prefix=QUERY_PREFIX)`; owns-connection RO path; `encoder` optional when `mode="keyword"`; assembles full-text hits from the two sets' rows.
    - Creative ref: both architecture docs.
5. **Read-time truncation + table formatting**
    - Files: `src/stockroom/search.py`, `tests/test_search.py`
    - Changes: `DETAIL_LEVELS`, `COMPACT_CHARS`, `SNIPPET_CHARS`; pure `_truncate(text, level)` with visible marker; `_format_hits(hits, *, detail)` (via/score columns, `(N results)` trailer). Truncation only in render — `SearchHit.text` untouched.
    - Creative ref: `creative-read-time-truncation.md`.
6. **CLI `main` + `_build_parser`**
    - Files: `src/stockroom/search.py`, `tests/test_search.py`
    - Changes: positional `query`; `-k/--limit`; `--mode {blend,keyword,semantic}` (default blend); `--detail {compact,snippet,full}` (default snippet); `--harness`; guards (empty query → 2, non-positive limit → 2, missing warehouse → 1) **before** building the encoder; build encoder via `encoder_factory` only when the mode needs semantic.
    - Creative ref: all three.
7. **Real-model end-to-end (torch-gated)**
    - Files: `tests/test_search.py`
    - Changes: `importorskip("torch")` blend test — paraphrase ranks its message first.
8. **Documentation**
    - Files: `SKILL.md` (search now wired — update the status/entrypoint list), `memory-bank/techContext.md` (new `Search (sr-search)` section), `memory-bank/systemPatterns.md` (the blend/RRF + read-time-truncation pattern).
    - Note: docs are implementation work, done in this milestone.

## Technology Validation

**No new technology — validation not required.** No new dependencies (keyword is built-in
`ILIKE`; FTS deliberately rejected), no `uv.lock` change, no migration/schema change.
Reuses `semantic`/`embed`/`warehouse`. The one load-bearing unknown (keyword mechanism)
was de-risked by a throwaway probe (DuckDB 1.5.4: `ILIKE` built-in and correct; FTS
un-bundled + stale-on-insert) recorded in `creative-keyword-search-mechanism.md`.

## Challenges & Mitigations

- **Touching stable m2 code (`run_semantic_search`)** → keep it strictly additive (new keyword-only param, default `None`); a regression test plus the unchanged existing m2 tests prove no behavior change.
- **Fusion candidate starvation** (a strong single-method hit ranked just past `limit` in its own list) → over-fetch `limit * CANDIDATE_FACTOR` from each half before fusing, then RRF-truncate to `limit` (named constant; mirrors m2's `OVERFETCH` idea).
- **Keyword `ILIKE` is an O(n) scan** → bounded by `LIMIT`; corpus scale matches m2's already-linear semantic scan; FTS documented as a deliberate future optimization if scale ever demands keyword ranking.
- **Keyword-only must not require torch** → build the encoder lazily, only when the mode runs semantic; assert with the `_never_built` factory.
- **Determinism for tests** (`ts` is NULL for Cursor) → `ORDER BY ts DESC NULLS LAST, ordinal DESC, message_id`; `FakeEncoder` is deterministic; RRF tiebreak is total.
- **Not violating no-truncation-at-rest** → `SearchHit.text` carries whole text; trimming lives only in `_format_*`; a test asserts the hit retains full text while the render is bounded.
- **Re-level check**: this is one coherent surface (single module) with no independent workstreams — meaty L3, **not** L4.

## Status

- [x] Component analysis complete
- [x] Open questions resolved
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [ ] Preflight
- [ ] Build
- [ ] QA
