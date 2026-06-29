# Task: Read-time output truncation

* Task ID: `p2-embeddings-search` (milestone m3 of 6)
* Complexity: Level 2
* Type: Simple enhancement (additive, contained — new shared mechanism + thin wiring into two existing renderers)

Build a **shared, tested read-time output-truncation mechanism** and wire it into the two existing read-surface renderers (`stockroom.query._format_table`, `stockroom.semantic._format_hits`). The mechanism collapses a cell to a single line and bounds it to a context-safe width with a **visible elision marker** (`…`), selectable via discrete detail levels (`compact | snippet | full`). `full` is the unbounded escape. Full content stays whole at rest and in the returned data objects (`QueryResult.rows`, `SemanticHit.text`) — trimming is render-time only (the no-truncation-at-rest invariant). This supersedes `semantic`'s ad-hoc `_preview`/`PREVIEW_CHARS` with the single shared mechanism, and gives `query` (which truncates nothing today) a context-safe default.

## Resolved design decisions

- **Default posture (resolves the milestone's open question).** Truncation is **on-by-default at `snippet`** for *both* surfaces, with `--detail full` as the escape and `--detail compact` for terser output. Rationale: the cap only affects cells exceeding the width, so narrow SQL results (counts, id columns) are visually untouched while wide `SELECT *`/long-`text` results are made context-safe by default — the phase's "sensibly trimmed on output" headline. The power-user escape (`full`) is one flag away.
- **Per-cell width cap, not a global/context-aware budget.** v1 bounds each *cell*; it does **not** implement a whole-output token/row budget. A global "context-aware" budget is explicitly **out of scope** (it would warrant a real budgeting design → L3). Per-cell elision is the L2 mechanism the milestone describes.
- **Single-line collapse applies at every level, including `full`.** Table cells must be single-line or column alignment breaks; this matches `semantic`'s current behavior. "Full content" fidelity is preserved by the data layer (`QueryResult.rows` / `SemanticHit.text`), not by the rendered table. `full` removes the *width* cap only.
- **Data cells only; column headers are not truncated** (they are short identifiers; widths are computed post-truncation so alignment stays correct regardless).
- **Levels are named, tunable module constants.** Starting widths: `compact=40`, `snippet=120`, `full=None` (unbounded). `semantic`'s preview default thus moves 80→120; acceptable and centralizes the single source of truth.
- **The elision marker reports how much was hidden** (e.g. `…(+482)`), not a bare `…` (preflight amendment). This turns truncation into an actionable signal for the downstream `sr-query`/`sr-semantic`/`sr-search` surfaces — the agent can see content was elided and roughly how much, and decide whether to re-fetch with `--detail full` or narrow the SQL (the creative doc's "guardrails against wasted tool calls"). The marker is appended **beyond** the level width (kept content == level width), so a truncated cell's rendered width is the level width plus a short, bounded marker.

## Test Plan (TDD)

### Behaviors to Verify

`stockroom.truncate.truncate_cell` (new):

- Short value, any level: `truncate_cell("hi", "snippet")` → `"hi"` (single-lined, unchanged, no marker).
- Over-width value: `truncate_cell("x"*602, "snippet")` → keeps 120 content chars then the hidden-count marker `…(+482)`; the full 602-char run is not present.
- Hidden-count is accurate: the marker's reported number equals `len(single_line) - width` (482 above), so it is an actionable "more exists" signal rather than a bare ellipsis.
- `full` level: `truncate_cell("x"*5000, "full")` → no marker, full content length preserved (still single-lined).
- Whitespace/newline collapse: `truncate_cell("a\n\nb  c", level)` → `"a b c"` for every level (incl. `full`).
- Level ordering: `compact` keeps fewer content chars than `snippet`, and `full` is unbounded — for a sufficiently long input the kept-content lengths satisfy `compact < snippet < full`.
- Exact-width boundary: a value exactly `LEVEL_WIDTHS["snippet"]` chars → unchanged, no marker; one char over → `width` content chars + `…(+1)`.
- Empty string → `""`.
- `LEVEL_WIDTHS` keys == `DETAIL_LEVELS`; `DEFAULT_DETAIL == "snippet"`.

`stockroom.query._format_table(columns, rows, *, detail=...)`:

- A cell longer than the snippet width is elided in the rendered table (`…` present, the full value absent) at the default detail.
- `detail="full"` renders the whole cell (full value present, no `…`).
- Narrow cells (`[(1,)]`, `NULL`) render identically to today (regression: existing `_format_table` tests still pass with the new default).

`stockroom.semantic._format_hits(hits, *, detail=...)`:

- A long `text` is elided at default detail (`…` present); `detail="full"` shows the full text.
- Preview is still a single physical line (regression: existing single-line test still passes).

CLI:

- `python -m stockroom.query "SELECT repeat('x',500) AS big"` (default) → output contains `…`, not 500 `x`s; with `--detail full` → contains all 500 `x`s (subprocess).
- `--detail compact` yields a shorter `big` cell than the default (subprocess).
- `stockroom.semantic.main(["--detail","full", <query>], encoder_factory=FakeEncoder)` prints the full long message text; default elides it (in-process).
- Invalid `--detail bogus` → argparse error, exit code 2 (both CLIs).

### Test Infrastructure

- Framework: `pytest`, configured in `skills/sr-search/pyproject.toml` (`[tool.pytest.ini_options]`); run via `make test` / `make ci` from repo root.
- Test location: `skills/sr-search/tests/`.
- Conventions: one `test_<module>.py` per module; pure renderers tested directly with literals; library entries tested against the injected `migrated_con` / `FakeEncoder` fixtures (`conftest.py`); CLI behavior split into in-process `main(...)` calls (semantic) and real subprocess runs (`test_query_cli.py`). Torch never required on these paths.
- New test files: `skills/sr-search/tests/test_truncate.py`.
- Modified test files: `test_query.py`, `test_semantic.py`, `test_query_cli.py`.

## Implementation Plan

1. **Stub the shared mechanism + its tests.**
   - Files: `skills/sr-search/src/stockroom/truncate.py` (new), `skills/sr-search/tests/test_truncate.py` (new).
   - Changes: define `DetailLevel = Literal["compact","snippet","full"]`, `DETAIL_LEVELS: tuple[str,...]`, `LEVEL_WIDTHS: dict[str,int|None]` (`40 / 120 / None`), `DEFAULT_DETAIL = "snippet"`, `ELISION = "…"` (the marker glyph), and `truncate_cell(value: str, detail: DetailLevel = DEFAULT_DETAIL) -> str` — empty body + full docstring. Stub all `test_truncate.py` cases empty, then implement them (they fail).
2. **Implement `truncate_cell`.**
   - Files: `truncate.py`.
   - Changes: single-line collapse (`" ".join(value.split())`), look up width, return as-is when `width is None` or `len(single_line) <= width`, else keep `single_line[:width]` and append the hidden-count marker `f"{ELISION}(+{len(single_line) - width})"`. Make `test_truncate.py` green.
3. **Wire truncation into the query renderer (test-first).**
   - Files: `test_query.py` (add `_format_table` truncation cases), then `query.py`.
   - Changes: `_format_table(columns, rows, *, detail: DetailLevel = DEFAULT_DETAIL)`; apply `truncate_cell(cell, detail)` to each stringified data cell before width computation; `main` gains `--detail` (`choices=DETAIL_LEVELS`, `default=DEFAULT_DETAIL`) passed through to `_format_table`. Update the module docstring (drop "truncation is m3's feature" framing; document the `--detail` flag).
4. **Wire truncation into the semantic renderer (test-first).**
   - Files: `test_semantic.py` (add/adjust `_format_hits` detail cases), then `semantic.py`.
   - Changes: `_format_hits(hits, *, detail: DetailLevel = DEFAULT_DETAIL)` uses `truncate_cell(hit.text or "", detail)` for the `preview` column; `main` gains `--detail` passed through; **remove** `PREVIEW_CHARS` and `_preview` (superseded). Update the module docstring/comments that defer truncation to m3.
5. **CLI end-to-end coverage.**
   - Files: `test_query_cli.py` (subprocess `--detail` cases), `test_semantic.py` (in-process `--detail` cases).
   - Changes: assert default-vs-`full`-vs-`compact` rendering and the invalid-`--detail` exit-2 path.
6. **Documentation.**
   - Files: in-code module docstrings in `query.py` / `semantic.py` (done in steps 3–4). Memory-bank pattern updates (`systemPatterns.md` "Semantic search…", `techContext.md` "Query"/"Semantic search" sections, which currently say truncation is deferred to m3) are folded into the Reflect/Archive phase per the Niko lifecycle, not the build.
7. **Full gate.** Run `make ci` from repo root; all tests green, `ruff` clean, `reuse` clean.

## Technology Validation

No new technology — validation not required. The mechanism is pure stdlib; `requires-python >= 3.11` already supports `Literal` and the `X | None` syntax used. No new dependency, so no `make lock` and no torch interaction.

## Dependencies

- Existing renderers `stockroom.query._format_table` and `stockroom.semantic._format_hits` (the wiring targets).
- `conftest.py` fixtures `migrated_con`, `warehouse_home`, `FakeEncoder` (already present; no changes needed).

## Challenges & Mitigations

- **Changing `semantic`'s default preview width (80→120).** Mitigation: it is a deliberate centralization; the existing `test_format_hits_previews_text_single_line` still passes (it truncates 500 chars and checks single-lining, not the exact width). Documented as a resolved decision above.
- **`full` on a pathologically wide cell still floods output.** Mitigation: that is the explicit power-user escape; the *default* (`snippet`) is the context-safe posture. Not a regression — `query` truncates nothing today.
- **Scope creep toward DRY-ing the two near-identical table renderers.** Mitigation: explicitly out of scope — this milestone adds a truncation mechanism, not a table-rendering refactor. Noted as a possible future improvement only.
- **Unicode/grapheme width.** Mitigation: use code-point `len()` (matches the existing `_preview`); true display-width handling is out of scope for v1.

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Preflight
- [x] Build
- [x] QA
