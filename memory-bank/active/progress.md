# Progress

Bring the Advanced docs section to presentation quality: power-user escape hatches (stockroom CLI out-of-band, DuckDB CLI; maybe successful direct `uv`), minimalism against User Guide overlap, landing + sub-pages shape preserved with content open to redesign.

**Complexity:** Level 3

## 2026-07-14 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - Intent restatement approved (scaffold shape right; content not set in stone)
    - Classified as Level 3
* Decisions made
    - Level 3: multi-page docs delivery with open content/IA decisions (creative warranted), parallel to architecture-docs
* Insights
    - Minimalism bias is the primary scope filter — exclude paths already in UG or uncertain as user workflows

## 2026-07-14 - CREATIVE - COMPLETE (topic inventory)

* Work completed
    - Explored encyclopedia vs duo vs trio vs recipes for Advanced topic cut
* Decisions made
    - **Option B — Escape-hatch duo**: Advanced owns out-of-band `stockroom` CLI + DuckDB CLI only
    - Omit direct end-user `uv`; omit catch-up ingest/embed / dashboard / heal-migrate deep dives (link UG / Contributing / `--help`)
* Insights
    - Shim exists because bare `uv` is the footgun; Contributing already owns checkout `uv`

## 2026-07-14 - CREATIVE - COMPLETE (page IA)

* Work completed
    - Explored single cli.md vs two satellites vs rename vs landing-heavy
* Decisions made
    - **Option B**: `index.md` + `cli.md` + new `duckdb.md`; keep `cli.md` slug for inbound links
* Insights
    - Two confirmed usages map 1:1 to two satellites under the locked landing + sub-pages shape

## 2026-07-14 - PLAN - COMPLETE

* Work completed
    - Full L3 plan in tasks.md: components, TDD behaviors B1–B6, implementation steps, challenges, pre-mortem
* Decisions made
    - Docs-only verification (content checklist + `make docs-build`); no pytest
    - DuckDB CLI recipe uses `-readonly` against `$STOCKROOM_HOME/warehouse.duckdb`
* Insights
    - Keep `cli.md` slug; add `duckdb.md`; rewrite scaffold encyclopedia away
