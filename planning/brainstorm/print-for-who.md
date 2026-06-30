# Brainstorm — Print for Who?

Decision record (2026-06-29): who the read-surface **stdout** is for, which CLI flags encode that, and how the upcoming `sr-*` skills should instruct LLMs to use them.

Feeds: L4 milestone **m3.5** (`memory-bank/active/milestones.md`), then the `sr-query` / `sr-semantic` / `sr-search` skill milestones.

## Problem

Phase 1 proved `stockroom.query` by printing an **ASCII column-aligned table** to the terminal. That made sense as a human end-to-end demo, but the primary consumption path for search surfaces is an **LLM reading tool output** (skills shell out to `python -m stockroom.query` / `.semantic`, ingest stdout into context, synthesize for the user).

Tables are a human conceit: pipes, padding, and separator art burn tokens without helping an agent reason. The load-bearing part of m3 is not the table renderer — it is **`truncate_cell`**: bounded read-time output with a visible elision marker (`…(+N)`) while full content stays whole at rest.

Third-party table libraries (tabulate, Rich, DuckDB `.show()`) solve generic tabular display; stockroom's custom contract is the **policy layer** (detail levels + informative elision). That policy applies regardless of output shape.

## Audience

| Consumer | Primary need | Default CLI posture |
|----------|--------------|------------------------|
| **LLM (via skills)** | Structured, bounded, parseable stdout; safe without reading a manual | `--format tsv` + `--detail snippet` |
| **Unix pipe processors** | Header row + one record per line; no alignment art; metadata off stdout | `--format tsv` |
| **Human at a terminal** | Pretty aligned columns when they just want to look | `--format table` (opt-in) |
| **User asking for a command** | Copy-paste-able incantation with the right flags for *their* need | Skill gives `--format table` or `--format json` examples on request |
| **Software** | Full structured data to process | `--format json` + `--detail full` |

The **library API** (`run_query` → `QueryResult`, `run_semantic_search` → `list[SemanticHit]`) is unchanged and always returns full structured data. Flags only affect the **CLI print boundary**.

## Two independent axes

### `--format` — output shape

| Value | Role | Default? |
|-------|------|----------|
| **`tsv`** | Header row + tab-separated data rows; pipe-friendly (`cut`, `awk`, `grep`, `wc -l`) | **yes** |
| **`json`** | Single JSON object (columns/rows or semantic result list); `jq`-friendly | no |
| **`table`** | Today's ASCII column-aligned table (human terminal) | no — opt-in |

**Default: `tsv`.**

TSV stdout should not include a `(N rows)` trailer — it breaks line-counting and stream processing. Row/result counts belong in stderr, in JSON fields, or omitted for `tsv`.

### `--detail` — per-string-field width (via `truncate_cell`)

| Value | Content char budget | Default? |
|-------|---------------------|----------|
| **`compact`** | 40 | no |
| **`snippet`** | 120 | **yes** |
| **`full`** | unbounded (still single-lined) | no — escape hatch |

**Default: `snippet`.**

Same mechanism in every format: collapse whitespace to one line; if over budget, keep the first *N* characters and append `…(+hidden)`. Under-budget cells are identical at every level. Not smart summarization — head truncation with an actionable "more exists" signal.

Implemented today in `stockroom.truncate` (m3). m3.5 wires it through all formatters, not only `_format_table`.

## Skill contract (for `sr-query`, `sr-semantic`, `sr-search`)

Skills are the **one place** operational advice lives (`creative-search-surface-architecture.md`). For print/format:

1. **Default invocation is safe.** An LLM can run the CLI with no extra flags and get bounded, parseable output (`--format tsv`, `--detail snippet`).
2. **Instruct `--detail full`** when the agent needs whole message text (or a specific narrow `SELECT`), especially after seeing `…(+N)`.
3. **Instruct `--detail compact`** when scanning many rows cheaply before picking one to re-fetch.
4. **Do not require humans to know the engine.** Relay findings in natural language; use the CLI as the tool, not as the user-facing product.
5. **When a user asks for copy-paste commands**, offer variants with `--format table` (human pretty-print) or `--format json` (structured) as appropriate — "these other options exist if you want them."

Skills may shell out to the CLI (current architecture) or call the library directly later; either way, the same defaults and flag semantics apply.

## Implementation (m3.5)

| Piece | Action |
|-------|--------|
| **`stockroom/render.py`** *(new)* | `format_query()`, `format_semantic()`; dispatch `tsv` / `json` / `table`; call `truncate_cell` when stringifying |
| **`query.py` / `semantic.py`** | Add `--format`; default `tsv`; `main()` prints via `render` |
| **`truncate.py`** | Unchanged — shared policy |
| **Tests** | New `test_render.py`; CLI tests expect `tsv` by default; `--format table` preserves current table assertions |
| **Wrapper skills** | Author *after* m3.5 so SKILL.md examples match shipped defaults |

Est. **L1/L2**: no schema, no new runtime deps, breaking change is CLI default only (subprocess tests).

## Decisions (settled)

| ID | Decision | Choice |
|----|----------|--------|
| PFW1 | Primary stdout consumer | LLM + pipe processors, not human table scanning |
| PFW2 | Default `--format` | **`tsv`** |
| PFW3 | Default `--detail` | **`snippet`** (unchanged from m3) |
| PFW4 | Human pretty-print | **`--format table`** (opt-in) |
| PFW5 | Structured alternative | **`--format json`** (opt-in; skill surfaces on user request) |
| PFW6 | Truncation policy location | **`stockroom.truncate`** — format-agnostic |
| PFW7 | Skill guidance | Defaults safe; `--detail full` when needed; `--format table`/`json` in user-facing command examples when asked |

## Non-goals (this pass)

- NDJSON streaming format (easy later: `--format ndjson`)
- Hoisting shared table layout into `render_table()` beyond moving existing `_format_table` (optional DRY; not blocking m3.5)
- Changing library return types or adding truncation inside `QueryResult` / `SemanticHit` — truncation stays at the print/serialize boundary
- Auto-detecting TTY to flip defaults (explicit flags only; skills document the contract)

## References

- m3 sub-run: `memory-bank/active/reflection/reflection-p2-embeddings-search-m3.md`
- Search-surface architecture: `memory-bank/active/creative/creative-search-surface-architecture.md`
- Truncation implementation: `skills/sr-search/src/stockroom/truncate.py`
