"""CLI + library: raw SQL against the warehouse (``python -m stockroom.query``).

The first user-facing read surface and the Phase-1 end-to-end proof: it opens
the warehouse **read-only** through the milestone-2 ``warehouse.open`` chokepoint,
executes arbitrary SQL, and prints the result.

Read-only **by construction**: the warehouse is rebuildable ETL output and this
surface exists to *interrogate* it, so DuckDB rejects writes through the
read-only connection. The lazy migration gate still runs (a reader behind the
schema head transparently becomes the migrator), so querying a stale warehouse
migrates it forward. The module mirrors ``stockroom.ingest``'s ``STOCKROOM_HOME``
env convention and its ``con``-injection / owns-connection shape.

Invoke as a single runnable module (no ``__main__.py`` — unlike the multi-module
``ingest`` package)::

    python -m stockroom.query "SELECT DISTINCT harness FROM sessions"
    echo "SELECT count(*) FROM messages" | python -m stockroom.query -
    python -m stockroom.query --format table "SELECT text FROM messages LIMIT 1"
    python -m stockroom.query --format json --detail full "SELECT * FROM sessions"

Output shape is selectable with ``--format`` (``tsv`` default — a header row plus
tab-separated data rows, no count trailer, stream-friendly for LLMs and unix
pipes; ``json``; ``table`` for a human pretty-print). Wide fields are truncated at
read time in every format (``--detail compact|snippet|full``, default ``snippet``)
so a long ``text`` column can't flood the caller's context; the full content
always stays whole in the warehouse (see :mod:`stockroom.render` and
:mod:`stockroom.truncate`).
"""

import argparse
import sys
from dataclasses import dataclass

import duckdb

from stockroom import render, warehouse
from stockroom.render import DEFAULT_FORMAT, OUTPUT_FORMATS
from stockroom.truncate import DEFAULT_DETAIL, DETAIL_LEVELS


@dataclass
class QueryResult:
    """The column names and rows produced by a single executed statement."""

    columns: list[str]
    rows: list[tuple]


def run_query(sql: str, *, con: duckdb.DuckDBPyConnection | None = None) -> QueryResult:
    """Execute ``sql`` and return its columns + rows.

    When ``con`` is ``None`` the warehouse is opened **read-only** through
    ``warehouse.open(read_only=True)`` (and closed on return); tests inject a
    connection. Any ``duckdb.Error`` (syntax error, read-only write rejection,
    …) propagates to the caller — the CLI ``main`` turns it into a clean message.
    """
    owns_connection = con is None
    connection = con if con is not None else warehouse.open(read_only=True)
    try:
        connection.execute(sql)
        columns = (
            [descriptor[0] for descriptor in connection.description]
            if connection.description
            else []
        )
        rows = connection.fetchall()
        return QueryResult(columns=columns, rows=rows)
    finally:
        if owns_connection:
            connection.close()


def _build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for ``python -m stockroom.query``."""
    parser = argparse.ArgumentParser(
        prog="python -m stockroom.query",
        description="Run raw read-only SQL against the stockroom warehouse.",
    )
    parser.add_argument(
        "sql",
        help="The SQL statement to run. Use '-' to read it from stdin.",
    )
    parser.add_argument(
        "--format",
        choices=OUTPUT_FORMATS,
        default=DEFAULT_FORMAT,
        help=(
            "Output shape: 'tsv' (default, header + tab-separated rows, no count "
            "trailer — stream-friendly for LLMs and unix pipes), 'json' (a single "
            "{columns, rows} object), or 'table' (human-readable pretty-print)."
        ),
    )
    parser.add_argument(
        "--detail",
        choices=DETAIL_LEVELS,
        default=DEFAULT_DETAIL,
        help=(
            "Read-time output detail: 'compact' (terse), 'snippet' (default, "
            "context-safe), or 'full' (untruncated). Wide cells are elided with a "
            "marker reporting how many characters were hidden; full content always "
            "stays whole in the warehouse."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Parse args, run the query read-only, print the table, return an exit code.

    Returns ``0`` on success, ``1`` on a query/warehouse error (with a clean
    stderr message and no traceback), and ``2`` on an empty query. The SQL is
    read from ``sys.stdin`` when the positional argument is ``-``.
    """
    args = _build_parser().parse_args(argv)
    sql = sys.stdin.read() if args.sql == "-" else args.sql

    if not sql.strip():
        print(
            "error: empty query (pass SQL as an argument, or '-' to read stdin)",
            file=sys.stderr,
        )
        return 2

    warehouse_file = warehouse.warehouse_path()
    if not warehouse_file.is_file():
        print(
            f"error: no warehouse found at {warehouse_file} — "
            "run `stockroom ingest` first",
            file=sys.stderr,
        )
        return 1

    try:
        result = run_query(sql)
    except duckdb.Error as exc:
        print(f"query failed: {exc}", file=sys.stderr)
        return 1

    print(
        render.format_query(
            result.columns, result.rows, fmt=args.format, detail=args.detail
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
