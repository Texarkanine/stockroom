# Task: `sr-query` — raw SQL query surface over the warehouse

* Task ID: p1-data-backbone-m5-sr-query
* Complexity: Level 2
* Type: Simple enhancement (new self-contained user-facing surface)

Milestone 5 of the `p1-data-backbone` L4 project, and the closing milestone of Phase 1. Ship the engine-level **raw-SQL query surface**: a `stockroom.query` module invoked as `python -m stockroom.query "<SQL>"` that opens the warehouse **read-only** through the milestone-2 `warehouse.open()` chokepoint, executes arbitrary SQL, and prints the result. This is the first user-facing read surface and the Phase-1 end-to-end proof: the database the prior four milestones built is real and queryable.

## Scope & Boundaries

- **In scope:** a new `src/stockroom/query.py` engine module + its `python -m stockroom.query` CLI; unit + subprocess tests; doc updates (`techContext.md`, README run-target example).
- **Out of scope (Phase 5, not this milestone):** a `skills/sr-query/` skill directory, its `SKILL.md` prompt wrapper, and the per-harness `/sr-query` invocation forms. Milestone 3 set the precedent — it shipped `python -m stockroom.ingest` as the engine surface with no skill dir. The polished skill/marketplace surface is explicitly Phase 5 roadmap work. Keeping that out is what holds this at L2.
- **Read-only by construction:** the query surface opens `warehouse.open(read_only=True)`. The warehouse is rebuildable ETL output; the query surface is for *interrogation*, so write statements are rejected by DuckDB's read-only connection (a feature, not a gap). The lazy migration gate still runs (a reader behind head becomes the migrator), so querying a stale warehouse migrates it forward.

## Test Plan (TDD)

### Behaviors to Verify

- **Render non-empty result**: `_format_table(["n"], [(1,)])` → a string with a header row naming `n` and a data row containing `1`.
- **Render empty result**: `_format_table(["n"], [])` → header present, no data rows (and a discernible "0 rows" signal).
- **`run_query` returns columns + rows (injected con)**: `run_query("SELECT 1 AS n", con=migrated_con)` → `columns == ["n"]`, `rows == [(1,)]`.
- **`run_query` over the real schema (injected con)**: after inserting a `sessions` row into `migrated_con`, `run_query("SELECT harness, project_id FROM sessions", con=...)` returns that row — proves queryability over the actual migrated schema.
- **`run_query` empty result set (injected con)**: `run_query("SELECT * FROM sessions WHERE 1=0", con=...)` → column names present, `rows == []`.
- **`run_query` opens read-only when `con is None`**: against an ingested `STOCKROOM_HOME` warehouse, `run_query("SELECT count(*) AS c FROM sessions")` returns the count and leaves the warehouse readable (connection closed). (Asserts the owns-connection open/close path.)
- **CLI happy path**: `python -m stockroom.query "SELECT 1 AS n"` against an ingested warehouse → exit 0, stdout contains the header `n` and the value `1`.
- **CLI proves end-to-end queryability**: after a `--full` ingest into a throwaway `STOCKROOM_HOME`, `python -m stockroom.query "SELECT DISTINCT harness FROM sessions ORDER BY harness"` → exit 0, stdout names both `cursor` and `claude` (the Phase-1 "Done When" proof, at the query layer).
- **Edge — invalid SQL**: `python -m stockroom.query "SELEKT 1"` → nonzero exit, a clean error message on stderr, **no Python traceback**.
- **Edge — read-only rejects writes**: `python -m stockroom.query "CREATE TABLE t (x INT)"` (or an `INSERT`) against a real warehouse → nonzero exit, error mentions read-only / cannot write; the warehouse is unchanged.
- **Edge — missing warehouse**: with `STOCKROOM_HOME` pointed at a dir holding no `warehouse.duckdb`, a query → nonzero exit with a friendly "no warehouse — run ingest first"-style message (not a raw `IOException`/traceback).
- **Edge — empty/blank SQL**: `python -m stockroom.query ""` (or only whitespace) → nonzero exit with a usage/empty-query message.
- **Edge — SQL from stdin**: `echo "SELECT 1 AS n" | python -m stockroom.query -` → exit 0, prints the result (the `-` sentinel reads stdin).

### Test Infrastructure

- **Framework**: `pytest`, configured in `skills/sr-search/pyproject.toml` (`[tool.pytest.ini_options]`); run via `make test` / `make ci` from repo root.
- **Test location**: `skills/sr-search/tests/`.
- **Conventions**: one `test_<area>.py` per area; unit tests use in-memory connections (`migrated_con` for the current schema, `schema_con` for frozen `0001`); subprocess/CLI end-to-end tests live in a dedicated `test_*_cli.py` that shells out via `subprocess.run` with `PYTHONPATH=<src>` and a throwaway `STOCKROOM_HOME` + env-pointed fixture roots (mirror `test_ingest_cli.py`). Reuse existing fixtures: `migrated_con`, `warehouse_home`, `cursor_root`, `claude_root`, `ai_tracking_db`.
- **New test files**: `tests/test_query.py` (unit: `_format_table`, `run_query` injected-con + read-only open path), `tests/test_query_cli.py` (subprocess end-to-end + edge cases).

## Implementation Plan

Each step is one RED→GREEN TDD cycle. Steps 1–2 are pure/unit (no DB); 3 adds the open path; 4–8 are the CLI; 9 docs; 10 the green gate.

1. **`_format_table(columns, rows) -> str` renderer**
   - Files: `tests/test_query.py` (new), `src/stockroom/query.py` (new).
   - Changes: stub `query.py` with module docstring + signatures (`run_query`, `_format_table`, `_build_parser`, `main`) and empty bodies; write + implement `_format_table` (header line + separator + one line per row; values `str()`-coerced, `NULL` for `None`; 0-row case prints header + a `(0 rows)` trailer). Deterministic, dependency-free.
2. **`run_query(sql, *, con=None)` over an injected connection**
   - Files: `tests/test_query.py`, `src/stockroom/query.py`.
   - Changes: implement the injected-con branch — `cur = con.execute(sql)`; `columns = [d[0] for d in cur.description] if cur.description else []`; `rows = cur.fetchall()`; return a small result (a `QueryResult` dataclass holding `columns: list[str]`, `rows: list[tuple]`, or a `(columns, rows)` tuple — pick the dataclass for self-documentation). Mirror the ingest `con is None` / `owns_connection` shape but defer the open path to step 3.
3. **`run_query` open-read-only path when `con is None`**
   - Files: `tests/test_query.py`, `src/stockroom/query.py`.
   - Changes: when `con is None`, `connection = warehouse.open(read_only=True)`, run, and `connection.close()` in `finally` (owns-connection pattern from `ingest.ingest`). Test against an ingested `warehouse_home`.
4. **CLI argument parser + happy path (`main`)**
   - Files: `tests/test_query_cli.py` (new), `src/stockroom/query.py`, `src/stockroom/query/__main__`? — **no**: a single module `stockroom/query.py` is directly runnable via `python -m stockroom.query` (no package/`__main__.py` needed, unlike the multi-module `ingest` package). Keep it one file.
   - Changes: implement `_build_parser` (positional `sql`; `prog="python -m stockroom.query"`) and `main(argv)` (parse → `run_query` → `print(_format_table(...))` → return 0); add `if __name__ == "__main__": raise SystemExit(main())`. First CLI subprocess test asserts exit 0 + rendered output.
5. **CLI SQL-error handling**
   - Files: `tests/test_query_cli.py`, `src/stockroom/query.py`.
   - Changes: wrap execution in `try/except duckdb.Error as exc:` → `print(f"query failed: {exc}", file=sys.stderr); return 1`. No traceback escapes.
6. **CLI read-only write rejection**
   - Files: `tests/test_query_cli.py`.
   - Changes: assert a `CREATE TABLE`/`INSERT` exits nonzero with a read-only error (behavior falls out of step-3 read-only open + step-5 error handling; this test pins it as a guarantee). Ingest a warehouse first so the connection opens.
7. **CLI missing-warehouse + empty-SQL edges**
   - Files: `tests/test_query_cli.py`, `src/stockroom/query.py`.
   - Changes: detect absent `warehouse.duckdb` (or catch the open-time `duckdb.IOException` whose message is *not* a lock conflict) → friendly "no warehouse found — run `python -m stockroom.ingest` first" on stderr, nonzero exit; reject empty/whitespace `sql` before opening with a usage message + nonzero exit.
8. **CLI stdin (`-`) SQL source**
   - Files: `tests/test_query_cli.py`, `src/stockroom/query.py`.
   - Changes: when `sql == "-"`, read the statement from `sys.stdin.read()`. Subprocess test pipes SQL via `input=`.
9. **Documentation**
   - Files: `memory-bank/techContext.md`, `README.md`.
   - Changes: add a "Query (`sr-query`)" subsection to `techContext.md` pointing at `stockroom.query` and the read-only/lazy-migrate behavior (sibling to the Ingest section); add a `python -m stockroom.query "<SQL>"` example to the README's ad-hoc-invocation block. (No `skills/` change — see Scope & Boundaries.)
10. **Green gate**
    - Files: none (verification).
    - Changes: `make ci` green (sync, lock-check, lint, format-check, test, reuse). New `.py` files are AGPL via the existing `REUSE.toml` code-within-skills globs — no per-file SPDX header (matches existing `src/`/`tests/` files).

## Technology Validation

No new technology — validation not required. `duckdb`, `argparse`, `sys`, `dataclasses` are all already in use; no new dependency, no `uv.lock` change.

## Dependencies

- Milestone 2 `warehouse.open(read_only=True)` chokepoint (lazy migration gate, reader backoff) — consumed as-is.
- Milestone 1+4 schema (`sessions`/`messages`/`tool_calls`/…, migrated through `0002`) — queried, not modified.
- Milestone 3 ingest (`python -m stockroom.ingest`) — used by CLI end-to-end tests to populate a throwaway warehouse.
- Existing fixtures: `migrated_con`, `warehouse_home`, `cursor_root`, `claude_root`, `ai_tracking_db` (`tests/conftest.py`).

## Challenges & Mitigations

- **Reading a non-existent warehouse**: `warehouse.open(read_only=True)` on a missing file raises a non-lock `duckdb.IOException` that propagates. *Mitigation*: pre-check `warehouse_path().is_file()` (or catch the non-lock IOException) and emit a friendly "run ingest first" message — covered by step 7's test.
- **Statements with no result set** (PRAGMA, write attempts): `cursor.description` may be `None`. *Mitigation*: guard `description` for `[]` columns; rely on read-only to reject writes (step 6).
- **Output format bikeshed**: a single deterministic text-table format is shipped (no `--format` flag) to honor YAGNI; richer formats are a later concern. *Mitigation*: `_format_table` is isolated and unit-tested, so adding a format later is a contained change.
- **Not a hidden L3**: one new module + two test files + doc edits, over already-built, already-populated infrastructure; no new architecture, no cross-cutting schema/ingest change. Stays L2. If preflight finds the surface must grow a skill wrapper or multiple output modes to be "done," re-level.

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [ ] Preflight
- [ ] Build
- [ ] QA
