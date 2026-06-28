# Progress

Milestone 5 of the `p1-data-backbone` L4 project: **`sr-query`** — raw SQL against the warehouse, the first user-facing surface, proving the database is real and queryable end to end. A single self-contained surface over the already-built, already-populated warehouse: the `warehouse.py` open helper, the `migrate.py` lazy version gate, and the schema migrated through `0002`. Preserves the L4 cross-milestone invariants (forward-only numbered migrations, harness-labeled single schema, no truncation at rest, green `make ci`, test-first).

**Complexity:** Level 2

## 2026-06-28 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - Re-entered `/niko` on the `p1-data-backbone` L4 project. Milestone 4 (`project_id` + `cwd` recovery) was `REFLECT COMPLETE`; checked it off in `milestones.md` and cleared its sub-run ephemeral files per Step 2a (`tasks.md`, `activeContext.md`, `progress.md`, `creative/`, `.qa-validation-status`, `.preflight-status`). Preserved `milestones.md`, the L4 `projectbrief.md`, and prior `reflection/` docs (now four: m1–m4).
    - Surveyed the `skills/sr-search/` engine to confirm the estimate: a mature `ingest` subpackage with its own `__main__.py` CLI surface, `warehouse.py` (harness-neutral open helper), `migrate.py` (lazy version gate), and the schema populated through migration `0002`.
    - Classified the next unchecked milestone (`sr-query`) as **Level 2**, matching the L4 plan estimate.
    - Created fresh sub-run ephemeral files (this `progress.md`, refreshed `activeContext.md`, stubbed `tasks.md`).
* Decisions made
    - **L2, not L3:** a single self-contained, user-facing surface over already-built, already-populated infrastructure — not a new architecture spanning multiple subsystems. The `ingest/__main__.py` CLI already establishes the surface/entrypoint convention to mirror. No creative phase needed.
* Insights
    - `sr-query` is the Phase-1 end-to-end proof: it closes the loop (schema → migration framework → ingest → query) by reading back the warehouse the prior four milestones built.

## 2026-06-28 - PLAN - COMPLETE (no creative phase)

* Work completed
    - Surveyed the full surface: `warehouse.open(read_only=…)` (lazy migration gate + reader backoff), the `ingest.ingest` con-injection / owns-connection convention, the `test_ingest_cli.py` subprocess pattern, the conftest fixtures (`migrated_con`/`warehouse_home`/`cursor_root`/`claude_root`/`ai_tracking_db`), and the authoritative `sr-query` spec in `planning/roadmap.md` + `planning/tech-brief.md`.
    - Wrote the L2 plan to `tasks.md`: 12 behaviors (incl. read-only write-rejection, missing-warehouse, invalid-SQL-no-traceback, stdin, empty-SQL edges) and a 10-step ordered TDD plan — `_format_table` → `run_query` injected-con → `run_query` read-only open path → CLI parser/happy-path → SQL-error handling → read-only rejection → missing-warehouse/empty-SQL → stdin → docs → green gate. New files: `src/stockroom/query.py`, `tests/test_query.py`, `tests/test_query_cli.py`.
* Decisions made
    - **Engine surface only:** `python -m stockroom.query`; no `skills/sr-query/` dir (Phase 5 scope) — mirrors m3 ingest, holds the milestone at L2.
    - **Read-only by construction** (DuckDB rejects writes through the query surface; lazy migrate still runs); **single runnable module** (no `__main__.py`); **one deterministic text-table format** (YAGNI on `--format`).
    - **No new technology** — `duckdb`/`argparse`/`dataclasses` only; no `uv.lock` change.
* Insights
    - The CLI's "DISTINCT harness over a freshly-ingested warehouse names both cursor and claude" test *is* the Phase-1 "Done When" proof expressed at the query layer — the loop closes here.

## 2026-06-28 - PREFLIGHT - PASS

* Work completed
    - Validated the plan against codebase reality (TDD per-unit encoding, convention compliance, dependency impact, conflict detection, completeness). Wrote `.preflight-status`.
    - Verified two load-bearing assumptions empirically: `REUSE.toml` annotation #3 globs `skills/**/*.py` + `skills/**/tests/**` to AGPL (no per-file header), and no existing read-only-open-on-missing-file path exists (`test_warehouse_open.py` only opens RO on a created warehouse) — confirming the missing-warehouse edge is new behavior the plan owns via a `warehouse_path().is_file()` pre-check.
* Amendments made to `tasks.md`
    - **A1 (TDD encoding):** rewrote all 10 steps with explicit per-step RED→GREEN ordering (was concentrated in the preamble); step 1 lands a signature-only stub so tests fail on behavior, not `ImportError`.
    - **A2 (radical innovation, in-scope, applied):** `_format_table` always emits a `(N rows)` trailer → self-describing query output, serving the milestone's "prove it's queryable" intent at trivial cost.
* Advisories (non-blocking)
    - `--format {csv,json}` and a `skills/sr-query/` SKILL.md wrapper + per-harness `/sr-query` invocation are Phase 5 distribution scope; deliberately not built here (would broaden beyond L2).
    - Querying a behind warehouse migrates it forward (reader-turned-migrator, m2 design) — intended lazy-gate behavior.
* Next
    - PREFLIGHT PASS → BUILD is autonomous (solid edge) in the L2 workflow. Proceed to `/niko-build`.

## 2026-06-28 - BUILD - COMPLETE

* Work completed (TDD, RED→GREEN per step; final `make ci` green: 184 passed (16 new), ruff clean, `uv.lock --locked`, REUSE 156/156)
    - **`src/stockroom/query.py`**: `QueryResult` dataclass; `_format_table` (column-aligned text table, `NULL` for `None`, always-on `(N rows)`/`(1 row)` trailer — amendment A2); `run_query(sql, *, con=None)` (injected-con fast path + owns-connection `warehouse.open(read_only=True)` path, mirroring `ingest.ingest`); `_build_parser` + `main` (`python -m stockroom.query`, a single runnable module — no `__main__.py`, unlike the `ingest` package).
    - **`tests/test_query.py`** (9 unit): renderer behaviors, `run_query` over injected `migrated_con` (incl. real-schema seeded `sessions` row + empty result), and the owns-connection read-only path (returns results; rejects writes).
    - **`tests/test_query_cli.py`** (7 subprocess): happy path, the end-to-end DISTINCT-harness proof (ingest→query names both cursor & claude), invalid-SQL clean error (no traceback), read-only write rejection, friendly missing-warehouse hint, empty-SQL rejection, stdin (`-`).
    - **Docs**: `techContext.md` "Query (`sr-query`)" section; README ingest→query example.
* Decisions made
    - **Read-only enforcement is the open mode, not app logic**: `run_query`/`main` open `read_only=True` and let DuckDB reject writes; the CLI just wraps `duckdb.Error` into a clean message. No allow/deny-list of statement types (KISS/YAGNI).
    - **Missing-warehouse via pre-check**: `warehouse.warehouse_path().is_file()` before opening (avoids depending on the exact non-lock `IOException` text), with the `duckdb.Error` catch as defense-in-depth.
    - **Built to plan, zero deviations.** The one RED false-positive (empty-SQL test passing on `NotImplementedError`) became a genuine pass once `main` shipped.
* Insights
    - The end-to-end CLI test (ingest a throwaway warehouse, then `SELECT DISTINCT harness` names both harnesses) closes the Phase-1 loop at the query layer — the milestone's whole reason for existing, demonstrated rather than asserted.
* Next
    - QA (`/niko-qa`) gates REFLECT for L2.

## 2026-06-28 - QA - PASS

* Work completed
    - Semantic review of the build against the `tasks.md` plan across all seven QA constraints (KISS / DRY / YAGNI / Completeness / Regression / Integrity / Documentation). All PASS; no trivial fixes needed (code shipped clean — debris sweep for TODO/print("HERE")/breakpoint clean).
    - Wrote `.qa-validation-status` (PASS) and checked off QA in `tasks.md`.
* Decisions made
    - The `con` parameter on `run_query` is **not** a YAGNI violation: it is the documented injected-connection test contract (exercised across the unit suite), mirroring `ingest.ingest`.
    - Read-only enforcement living in the open mode (DuckDB rejects writes) rather than an app-level statement allow/deny-list is the correct KISS posture — no validation layer to maintain or get wrong.
* Insights
    - Mechanical gate (`make ci`) and semantic gate agree: the surface integrates as a natural extension of the `warehouse.open()` chokepoint, not an accretion layer. The only carry-forward is a possible durable `systemPatterns` generalization, deferred to REFLECT.
* Next
    - QA PASS → REFLECT (autonomous) per the L2 workflow.
