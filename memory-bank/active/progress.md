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

## 2026-07-10 - PLAN - COMPLETE

* Work completed
    - Linear TDD plan in `tasks.md` (orchestrator/embed `on_progress` → CLI `--verbose` → docs)
    - Technology validation: no new dependencies
* Decisions made
    - Optional `on_progress: Callable[[str], None] | None` in library; CLI passes `print` only when `--verbose`
    - Progress denominator = selected discovered conversations (not subagent-inflated write count)
    - Elapsed time / skip stats are verbose-only CLI prints, not `IngestSummary` API changes
* Insights
    - House style already uses injection (`encoder_factory`); progress callbacks fit the same seam

## 2026-07-10 - PREFLIGHT - COMPLETE

* Work completed
    - Validated plan against ingest/embed call sites and CLI test conventions
    - Amended plan: explicit test-before-code per unit; `flush=True` on progress prints
    - Wrote `.preflight-status` = PASS
* Decisions made
    - No shared progress module; duplicate thin `print(..., flush=True)` wiring at two CLIs is fine
    - Optional `on_progress` default keeps `test_semantic` / dashboard ingest callers unchanged
* Insights
    - All production callers use keyword defaults; signature extension is non-breaking

## 2026-07-10 - BUILD - COMPLETE

* Work completed
    - `on_progress` on ingest + embed_pending; `--verbose` on both CLIs
    - Tests extended; docs updated; lint clean; 475 passed, 3 skipped
* Decisions made
    - Deferred elapsed-time nice-to-have
* Insights
    - None beyond plan

## 2026-07-10 - QA - COMPLETE

* Work completed
    - Semantic review PASS; no trivial fixes needed
* Decisions made
    - Duplicate one-line `ProgressCallback` alias across ingest/embed left as-is (shared module still YAGNI)
* Insights
    - Implementation matches plan; quiet-default and verbose paths covered
