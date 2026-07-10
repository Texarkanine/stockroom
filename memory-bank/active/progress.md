# Progress

Add `--verbose` progress logging to `python -m stockroom.ingest` and `python -m stockroom.embed` so long runs show human-readable progress while staying quiet by default for CI/tests; preserve end-of-run summaries and keep the suite green ([issue #1](https://github.com/Texarkanine/stockroom/issues/1)).

**Complexity:** Level 2

## 2026-07-10 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - Intent clarified and approved
    - Classified as Level 2
    - Ephemeral memory bank initialized
* Decisions made
    - Level 2: enhancement across ingest + embed CLIs with a shared quiet-by-default / `--verbose` contract; no architecture change
* Insights
    - Issue already specifies flag semantics and acceptance criteria; design work is mostly where to hook progress callbacks
