# Task: Output format defaults (`--format`)

* Task ID: `p2-embeddings-search` (milestone m3.5 of 7)
* Complexity: Level 2
* Type: Simple enhancement (additive presentation chokepoint + thin CLI wiring; one clean-break default flip)

Introduce a shared `stockroom.render` presentation chokepoint that owns all rendered output for the two read surfaces. It exposes two public functions — `format_query(columns, rows, *, fmt, detail)` and `format_semantic(hits, *, fmt, detail)` — each dispatching on `fmt`:

- **`tsv`** *(new default)* — a header row plus one tab-separated record per row; **no `(N rows)`/`(N results)` trailer** (it breaks line-counting / stream processing). Stream-friendly for LLMs and unix pipes.
- **`json`** — a single JSON object (`{"columns", "rows"}` for query; `{"results": [...]}` for semantic); `jq`-friendly.
- **`table`** — today's ASCII column-aligned table *with* its `(N rows)`/`(N results)` trailer; an opt-in human pretty-print.

The existing `--detail {compact,snippet,full}` (default `snippet`) governs per-string-field width **in every format** via the unchanged `stockroom.truncate.truncate_cell`. Both CLIs gain a `--format {tsv,json,table}` flag (default `tsv`). The library entries (`run_query` → `QueryResult`, `run_semantic_search` → `list[SemanticHit]`) are **unchanged** and always return full structured data — flags affect only the CLI print boundary. Decision record: `planning/brainstorm/print-for-who.md` (PFW1–PFW7).

## Resolved design decisions

- **`render` is the single presentation home.** The two existing private renderers move out of their modules into `render` as the `table` branch: `query._format_table` → `render`'s query-table helper, `semantic._format_hits` → `render`'s semantic-table helper. Per the decision record this milestone *moves* them; it does **not** further DRY the two table layouts into one shared `render_table()` (explicit non-goal — that optional consolidation is the standing m3 insight, deliberately out of scope here).
- **No import cycle.** `query`/`semantic` import `render` at runtime (for the dispatchers + the `OUTPUT_FORMATS`/`DEFAULT_FORMAT` argparse constants, mirroring how they already import `DETAIL_LEVELS`/`DEFAULT_DETAIL` from `truncate`). `render` imports `QueryResult`/`SemanticHit` only under `TYPE_CHECKING` (with `from __future__ import annotations`), so the runtime edge is strictly one-way `query|semantic → render`.
- **Truncation is format-agnostic and uniform.** Every format stringifies through `truncate_cell` at the chosen `detail`. Consequence (documented): JSON string values are single-lined and elided at `snippet` by default — `--detail full` restores full (still single-lined) content; true multi-line / typed fidelity is the **library**, not the CLI (non-goal to change return types or truncate at rest).
- **JSON type handling.** SQL `NULL` → JSON `null`; every non-null query cell is the `truncate_cell(str(v))` string (uniform with tsv/table — numeric columns serialize as strings, the documented tradeoff). Semantic `score` stays a JSON number (`round(1 - distance, 3)`); `rank` an int; `text` the `truncate_cell`'d string. `json.dumps(..., ensure_ascii=False)` so the `…` marker stays readable.
- **Counts are a table-only human affordance.** The `(N rows)`/`(N results)` trailer is kept **only** in `table`; omitted from `tsv` and `json` (derivable; honors the "no trailer in tsv" constraint). Not emitted to stderr.
- **`NULL` literal** still renders as `NULL` in `tsv` and `table` (preserves the existing table contract / tests); `json` uses native `null`.
- **TSV structural safety is free** (preflight finding). `truncate_cell` single-lines via `" ".join(value.split())`, and `str.split()` with no args splits on **all** whitespace including `\t` and `\n`. So no raw tab/newline can leak into a tsv field and corrupt the column structure — at **every** detail level, including `full`. The tsv renderer therefore needs no extra escaping; it relies on the existing truncation policy's whitespace collapse.

## Test Plan (TDD)

### Behaviors to Verify

`stockroom.render.format_query(columns, rows, *, fmt=DEFAULT_FORMAT, detail=DEFAULT_DETAIL)` (new):

- **tsv shape**: `format_query(["a","b"], [("1","2")], fmt="tsv")` → line 1 is `a\tb`, line 2 is `1\t2`; output contains **no** `" | "` and **no** `(… row` trailer.
- **tsv truncation**: a cell wider than the snippet budget at default detail → `ELISION` present, the full value absent; `fmt="tsv", detail="full"` → full value present, no `ELISION`.
- **tsv empty**: `format_query(["n"], [], fmt="tsv")` → header line `n` only, no trailer.
- **json shape**: `json.loads(format_query(["a","b"], [("1","2")], fmt="json"))` → `{"columns": ["a","b"], "rows": [["1","2"]]}`.
- **json null**: a `None` cell serializes to JSON `null` (not `"NULL"`).
- **json truncation**: a wide string cell is elided at default detail (`ELISION` in the parsed value); `detail="full"` keeps it whole.
- **table parity** (relocated `_format_table` behaviors): `fmt="table"` renders header + value and ends with `(1 row)`; `(0 rows)` for empty; pluralizes `(2 rows)`; `None` → `NULL`; a wide cell is elided at default and whole at `detail="full"`.

`stockroom.render.format_semantic(hits, *, fmt=DEFAULT_FORMAT, detail=DEFAULT_DETAIL)` (new):

- **tsv shape**: header line `rank\tscore\tharness\trole\tpreview`; one tab-separated line per hit; no `(… result` trailer; `score` rendered as `1 - distance`.
- **tsv truncation**: a long `text` is single-lined + elided at default detail; `detail="full"` keeps it whole.
- **json shape**: `json.loads(...)` → `{"results": [ {rank:int, score:number≈1-distance, harness, session_id, message_id, role, text}, … ]}`; `text` is `truncate_cell`'d at detail (full keeps whole); `score` is a JSON number.
- **table parity** (relocated `_format_hits` behaviors): `fmt="table"` shows a similarity `score`, previews `text` on a single physical line (elided at default), `detail="full"` keeps the whole text with no `ELISION`, and empty hits render `(0 results)`.

CLI — query (subprocess, `test_query_cli.py`):

- **default is tsv**: `python -m stockroom.query "SELECT 1 AS n"` → stdout contains `n` and `1`, but **no** `" | "` and **no** `(1 row)` trailer.
- **`--format table`**: same query with `--format table` → stdout contains `" | "` and `(1 row)`.
- **`--format json`**: `json.loads(stdout)` succeeds and has `columns`/`rows` keys.
- **invalid format**: `--format bogus` → exit code 2 (argparse), before warehouse access.

CLI — semantic (in-process `main(...)`, `test_semantic.py`):

- **default is tsv**: `main(["the unique findable phrase"], encoder_factory=FakeEncoder)` → stdout contains the phrase, a tab-separated `rank`…`preview` header, and **no** `(1 result)` trailer.
- **`--format table`**: `main(["--format","table", …])` → stdout contains `(1 result)`.
- **`--format json`**: `json.loads(stdout)` → `results[0].text` contains the phrase; `results[0].score` is a number.
- **invalid format**: `main(["--format","bogus", …])` → exit code 2.
- **regression**: the limit test counts tsv data lines (or asserts via `--format table`) rather than the removed default trailer.

### Test Infrastructure

- Framework: `pytest`, configured in `skills/sr-search/pyproject.toml` (`[tool.pytest.ini_options]`, `pythonpath=["src"]`); run via `make test` / `make ci` from repo root.
- Test location: `skills/sr-search/tests/`.
- Conventions: one `test_<module>.py` per module; pure renderers tested with literals; CLI behavior split into real subprocess runs (`test_query_cli.py`) and in-process `main(...)` calls (semantic, via `FakeEncoder`). Torch never required on these paths.
- New test files: `skills/sr-search/tests/test_render.py`.
- Modified test files: `test_query.py` (remove the relocated `_format_table` tests; keep the `run_query` tests untouched), `test_semantic.py` (remove the relocated `_format_hits` tests; fix the two trailer-asserting CLI tests for the new tsv default; add `--format` CLI tests), `test_query_cli.py` (add `--format` subprocess tests).

## Implementation Plan

1. **Stub `render` + its tests.**
   - Files: `skills/sr-search/src/stockroom/render.py` (new), `skills/sr-search/tests/test_render.py` (new).
   - Changes: `from __future__ import annotations`; define `OutputFormat = Literal["tsv","json","table"]`, `OUTPUT_FORMATS: tuple[str,...] = ("tsv","json","table")`, `DEFAULT_FORMAT: OutputFormat = "tsv"`; `format_query(columns: list[str], rows: list[tuple], *, fmt: OutputFormat = DEFAULT_FORMAT, detail: DetailLevel = DEFAULT_DETAIL) -> str` and `format_semantic(hits: list[SemanticHit], *, fmt=DEFAULT_FORMAT, detail=DEFAULT_DETAIL) -> str` — empty bodies + full docstrings; `TYPE_CHECKING` import of `QueryResult`/`SemanticHit` for annotations only. Stub all `test_render.py` cases empty, then implement them (red).
2. **Implement `render`.**
   - Files: `render.py`.
   - Changes: move the body of `query._format_table` into a private `_query_table(columns, rows, *, detail)` and `semantic._format_hits` into `_semantic_table(hits, *, detail)` (verbatim — incl. their `(N rows)`/`(N results)` trailers); add `_query_tsv` / `_query_json` and `_semantic_tsv` / `_semantic_json` helpers (or inline) applying `truncate_cell`; the two public functions dispatch on `fmt` (`tsv`/`json`/`table`). `json.dumps(..., ensure_ascii=False)`; SQL `None` → JSON `null`; semantic `score` numeric. Make `test_render.py` green.
3. **Wire the query CLI (test-first).** *(preflight amendment: the query CLI `--format` tests are written **before** the `query.py` wiring, so this unit is itself test-first rather than validated two steps later.)*
   - Files: `test_query.py` (delete the `_format_table` block + its import of `_format_table`; the `run_query` tests stay) and `test_query_cli.py` (add the `--format` subprocess assertions — default-is-tsv: no `" | "`, no `(N rows)`; `--format table` restores both; `--format json` parses; invalid `--format` → exit 2), **then** `query.py`.
   - Changes: `query.py` imports `render` (+ `OUTPUT_FORMATS`, `DEFAULT_FORMAT`); **remove** `_format_table`; add `--format` (`choices=OUTPUT_FORMATS`, `default=DEFAULT_FORMAT`); `main` prints `render.format_query(result.columns, result.rows, fmt=args.format, detail=args.detail)`. Update the module docstring (default `tsv`; `--format` usage examples). The new subprocess tests go red, then green.
4. **Wire the semantic CLI (test-first).**
   - Files: `test_semantic.py` (delete the `_format_hits` block; fix `test_cli_prints_ranked_results` + `test_cli_limit_flag_caps_results` for the tsv default; add `--format` CLI cases — default-is-tsv / `--format table` trailer / `--format json` parse / invalid → exit 2), **then** `semantic.py`.
   - Changes: `semantic.py` imports `render` (+ `OUTPUT_FORMATS`, `DEFAULT_FORMAT`); **remove** `_format_hits`; add `--format`; `main` prints `render.format_semantic(hits, fmt=args.format, detail=args.detail)`. Update the module docstring.
5. **Documentation.**
   - Files: `render.py`/`query.py`/`semantic.py` docstrings (done in steps 1–4); update `truncate.py`'s module docstring reference from `stockroom.query._format_table` / `stockroom.semantic._format_hits` to `stockroom.render` (the renderers moved). Memory-bank persistent-doc updates (`systemPatterns.md` "No truncation at rest" / `techContext.md` "Query"/"Semantic search"/"Read-time truncation" sections, which mention `_format_table`/`_format_hits`, `(N rows)`, and "column-aligned text table") are folded into the REFLECT phase per the Niko lifecycle, not the build.
6. **Full gate.** Run `make ci` from repo root; all tests green, `ruff` lint+format clean, `reuse` clean.

## Technology Validation

No new technology — validation not required. `json` is stdlib; `requires-python >= 3.11` already supports `Literal` and the `X | None` syntax used. No new dependency, so no `make lock` and no torch interaction.

## Dependencies

- The two existing renderers being relocated: `stockroom.query._format_table`, `stockroom.semantic._format_hits` (confirmed referenced only within their own modules, their tests, and one `truncate.py` docstring — no external consumers).
- The unchanged `stockroom.truncate` mechanism (`truncate_cell`, `DETAIL_LEVELS`, `DEFAULT_DETAIL`, `DetailLevel`, `ELISION`).
- `conftest.py` fixtures `migrated_con`, `warehouse_home`, `FakeEncoder` (already present; no changes needed).

## Challenges & Mitigations

- **Import cycle (`render` ↔ `query`/`semantic`).** Mitigation: runtime edge is one-way (`query`/`semantic` import `render`); `render` imports the dataclasses only under `TYPE_CHECKING` with `from __future__ import annotations`. Verified by `make ci` import-time success.
- **The `tsv` default flips behavior and breaks trailer-asserting tests.** The semantic CLI tests assert `(1 result)` / `(2 results)`, which the new default omits. Mitigation: per the decision record, update those to assert tsv shape (data-line count) or pin them to `--format table`; add explicit default-is-tsv assertions so the flip is itself tested.
- **JSON type fidelity.** Query cells stringify via `truncate_cell` (numbers become strings; `NULL` → `null`); only semantic `score` stays numeric. Mitigation: documented as a deliberate, decision-record-aligned tradeoff — the library is the full-typed-fidelity surface; richer typed JSON is an explicit non-goal/future enhancement.
- **`truncate_cell` single-lines even at `full`.** JSON `--detail full` text is full-length but whitespace-collapsed. Mitigation: documented — the truncation policy is format-agnostic by design (PFW6); multi-line fidelity lives in the data layer, not the print boundary.
- **Relocating private renderers invalidates doc references.** Mitigation: update `truncate.py`'s docstring in build (step 6); persistent-doc references are reconciled in REFLECT per the lifecycle (the m3 precedent).
- **Scope creep toward DRY-ing the two table layouts into one `render_table()`.** Mitigation: explicit non-goal; this milestone *moves* the two renderers, it does not merge them. Noted as the standing future consolidation only.

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Preflight
- [x] Build
- [x] QA

## QA Results

PASS. KISS/YAGNI/Integrity/Completeness/Regression clean. The two DRY items (the duplicated table-layout `widths`/`_line`, the semantic row projection, and the `1.0 - distance` score computation, all now localized within `render`) are the plan-sanctioned deferred consolidation — a future single `render_table(columns, rows, *, detail)` is the clean fix and would rework any piecemeal DRY done now, so deferring whole is correct (m3 precedent). Persistent-doc references (`systemPatterns.md`/`techContext.md`) are lifecycle-scheduled to REFLECT, not a build deficiency. No trivial fixes were needed.
