"""Shared output rendering for the warehouse read surfaces.

The Phase-2 milestone-3.5 presentation chokepoint: the single home for *how*
``stockroom.query`` and ``stockroom.semantic`` turn their results into printed
output. Two public entrypoints — :func:`format_query` and :func:`format_semantic`
— each dispatch on an output ``fmt``:

* ``tsv`` *(the default)* — a header row plus one tab-separated record per row,
  with **no** ``(N rows)`` / ``(N results)`` trailer. Stream-friendly for LLMs
  reading tool output and for unix pipe processors (``cut``, ``awk``, ``wc -l``).
* ``json`` — a single JSON object (``{"columns", "rows"}`` for query;
  ``{"results": [...]}`` for semantic), ``jq``-friendly.
* ``table`` — the human-facing ASCII column-aligned table (with its
  ``(N rows)`` / ``(N results)`` trailer); an opt-in pretty-print.

The orthogonal ``--detail`` axis (``compact | snippet | full | raw``, default
``snippet``) governs per-string-field width in **every** format via the shared
:func:`stockroom.truncate.truncate_cell` policy — so truncation is uniform and
format-agnostic. Non-``raw`` levels collapse all whitespace (including tabs and
newlines) to single spaces, so the ``tsv`` shape is structurally safe (no raw
delimiter can leak into a field) without extra escaping. ``raw`` preserves
stored whitespace; prefer ``--format json --detail raw`` for exact-text retrieval.

Truncation lives strictly at this **print boundary**: the library entries
(``run_query`` → ``QueryResult``, ``run_semantic_search`` → ``list[SemanticHit]``)
are unchanged and always carry full structured data. The runtime import edge is
one-way — ``query`` / ``semantic`` import ``render``; ``render`` imports their
dataclasses only under :data:`typing.TYPE_CHECKING`.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Literal

from stockroom.truncate import DEFAULT_DETAIL, DetailLevel, truncate_cell

if TYPE_CHECKING:
    from stockroom.semantic import SemanticHit

#: The ranked-result columns shown by the semantic ``tsv`` / ``table`` shapes.
_SEMANTIC_COLUMNS = ("rank", "score", "harness", "role", "preview")

#: A selectable output shape. ``tsv`` is the default.
OutputFormat = Literal["tsv", "json", "table"]

#: Ordered ``--format`` choices for the CLIs. The first entry is not the default
#: — :data:`DEFAULT_FORMAT` is — this is just the option list.
OUTPUT_FORMATS: tuple[str, ...] = ("tsv", "json", "table")

#: On-by-default output shape: stream-friendly for LLMs and unix pipes.
DEFAULT_FORMAT: OutputFormat = "tsv"


def format_query(
    columns: list[str],
    rows: list[tuple],
    *,
    fmt: OutputFormat = DEFAULT_FORMAT,
    detail: DetailLevel = DEFAULT_DETAIL,
) -> str:
    """Render a SQL ``QueryResult``'s ``columns`` + ``rows`` in ``fmt``.

    Every cell is stringified through :func:`stockroom.truncate.truncate_cell` at
    ``detail`` (SQL ``NULL`` → ``"NULL"`` for ``tsv``/``table``, JSON ``null`` for
    ``json``). ``tsv`` and ``json`` omit the row-count trailer; ``table`` keeps it.
    """
    if fmt == "tsv":
        lines = ["\t".join(columns)]
        lines.extend(
            "\t".join(
                truncate_cell("NULL" if v is None else str(v), detail) for v in row
            )
            for row in rows
        )
        return "\n".join(lines)
    if fmt == "json":
        payload = {
            "columns": columns,
            "rows": [
                [None if v is None else truncate_cell(str(v), detail) for v in row]
                for row in rows
            ],
        }
        return json.dumps(payload, ensure_ascii=False)
    if fmt == "table":
        return _query_table(columns, rows, detail=detail)
    raise ValueError(f"unknown output format: {fmt!r}")


def format_semantic(
    hits: list[SemanticHit],
    *,
    fmt: OutputFormat = DEFAULT_FORMAT,
    detail: DetailLevel = DEFAULT_DETAIL,
) -> str:
    """Render ranked semantic ``hits`` in ``fmt``.

    ``score`` is cosine *similarity* (``1 - distance``); the ``preview`` / ``text``
    field is passed through :func:`stockroom.truncate.truncate_cell` at ``detail``.
    ``tsv`` and ``json`` omit the result-count trailer; ``table`` keeps it. ``json``
    additionally carries the ``session_id`` / ``message_id`` identifiers and a
    numeric ``score``.
    """
    if fmt == "tsv":
        lines = ["\t".join(_SEMANTIC_COLUMNS)]
        lines.extend(
            "\t".join(
                [
                    str(hit.rank),
                    f"{1.0 - hit.distance:.3f}",
                    hit.harness,
                    hit.role,
                    truncate_cell(hit.text or "", detail),
                ]
            )
            for hit in hits
        )
        return "\n".join(lines)
    if fmt == "json":
        payload = {
            "results": [
                {
                    "rank": hit.rank,
                    "score": round(1.0 - hit.distance, 3),
                    "harness": hit.harness,
                    "session_id": hit.session_id,
                    "message_id": hit.message_id,
                    "role": hit.role,
                    "text": truncate_cell(hit.text or "", detail),
                }
                for hit in hits
            ]
        }
        return json.dumps(payload, ensure_ascii=False)
    if fmt == "table":
        return _semantic_table(hits, detail=detail)
    raise ValueError(f"unknown output format: {fmt!r}")


def _query_table(
    columns: list[str], rows: list[tuple], *, detail: DetailLevel = DEFAULT_DETAIL
) -> str:
    """Render a query result as a deterministic, column-aligned text table.

    Columns are left-aligned to their widest cell; ``None`` renders as ``NULL``.
    Each data cell is passed through :func:`stockroom.truncate.truncate_cell` at
    ``detail`` so a wide column cannot blow out the caller's context — full
    content stays whole in ``QueryResult.rows``; ``detail="full"`` renders it
    verbatim. Column headers are not truncated. The output always ends with a
    ``(N rows)`` / ``(1 row)`` trailer so the table is self-describing for any
    result size (including the empty case and statements with no result columns).
    """
    str_rows = [
        [truncate_cell("NULL" if v is None else str(v), detail) for v in row]
        for row in rows
    ]
    widths = [len(name) for name in columns]
    for str_row in str_rows:
        for index, cell in enumerate(str_row):
            widths[index] = max(widths[index], len(cell))

    def _line(cells: list[str]) -> str:
        return " | ".join(cell.ljust(widths[index]) for index, cell in enumerate(cells))

    lines: list[str] = []
    if columns:
        lines.append(_line(columns))
        lines.append("-+-".join("-" * width for width in widths))
    lines.extend(_line(str_row) for str_row in str_rows)

    count = len(rows)
    lines.append(f"({count} row{'' if count == 1 else 's'})")
    return "\n".join(lines)


def _semantic_table(
    hits: list[SemanticHit], *, detail: DetailLevel = DEFAULT_DETAIL
) -> str:
    """Render ranked hits as a column-aligned table with a similarity score.

    ``score`` is cosine *similarity* (``1 - distance``, rounded), computed at
    display time from the canonical :attr:`SemanticHit.distance`. ``preview`` is
    the message text passed through :func:`stockroom.truncate.truncate_cell` at
    ``detail``: collapsed to a single line and bounded to a context-safe width —
    a *display* bound only, the full text staying whole in
    :attr:`SemanticHit.text` (``detail="full"`` renders it untruncated). Always
    ends with a ``(N results)`` / ``(1 result)`` trailer, including the empty case.
    """
    columns = list(_SEMANTIC_COLUMNS)
    rows = [
        [
            str(hit.rank),
            f"{1.0 - hit.distance:.3f}",
            hit.harness,
            hit.role,
            truncate_cell(hit.text or "", detail),
        ]
        for hit in hits
    ]

    widths = [len(name) for name in columns]
    for row in rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))

    def _line(cells: list[str]) -> str:
        return " | ".join(cell.ljust(widths[index]) for index, cell in enumerate(cells))

    lines = [_line(columns), "-+-".join("-" * width for width in widths)]
    lines.extend(_line(row) for row in rows)
    count = len(hits)
    lines.append(f"({count} result{'' if count == 1 else 's'})")
    return "\n".join(lines)
