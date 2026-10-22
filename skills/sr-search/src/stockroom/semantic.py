"""CLI + library: pure vector search over the warehouse (``python -m stockroom.semantic``).

The Phase-2 milestone-2 read surface. It embeds a natural-language query with the
same ``sentence-transformers`` model the m1 pipeline used and ranks **every
stored vector exactly** by cosine distance. Multi-chunk hits are deduped to the
nearest chunk per owner message (the "max-sim" obligation m1 deferred) before
the cut to the limit, and only the winners are joined back to their
``messages`` rows for text. Optional ``--harness`` and ``--role`` filter before
the cut. Printing is a ranked table — all **read-only** through the
``warehouse.open()`` chokepoint.

Named ``semantic`` (not ``search``) so a keyword-search seeker doesn't grab it by
mistake: this is *pure* vector search. The blended, LLM-routed keyword + semantic
entrypoint is the separate ``sr-search`` skill.

Output shape is selectable with ``--format`` (``tsv`` default — a header row plus
tab-separated rows, no count trailer; ``json``; ``table`` for a human
pretty-print; see :mod:`stockroom.render`). The ``preview`` / ``text`` field is
truncated at read time in every format via the shared :mod:`stockroom.truncate`
mechanism (``--detail compact|snippet|full|raw``, default ``snippet``) — a
*display* bound only: the full text stays whole in the store and in
``SemanticHit.text``. ``--detail full`` renders it untruncated but single-line;
``--detail raw`` preserves exact whitespace (prefer with ``--format json``).

It mirrors ``stockroom.query``'s shape — a single runnable module (no
``__main__.py``) with a ``run_*`` library entry and a ``con``/encoder injection
seam — and reuses ``stockroom.embed``'s ``Encoder`` / ``BgeEncoder`` / ``EMBED_*``
so no embedding logic is duplicated::

    python -m stockroom.semantic "how does the warehouse lock work"
    python -m stockroom.semantic -k 5 "incremental re-embed"
    python -m stockroom.semantic --format json --detail raw "incremental re-embed"
"""

import argparse
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import duckdb

from stockroom import render, warehouse
from stockroom.embed import EMBED_DIM, BgeEncoder, Encoder, start_encoder
from stockroom.engine_env import EnsureReport
from stockroom.render import DEFAULT_FORMAT, OUTPUT_FORMATS
from stockroom.truncate import DEFAULT_DETAIL, DETAIL_LEVELS

#: bge-small-en-v1.5 is an *asymmetric* retrieval model: passages are embedded
#: with no prefix (m1), but the **query** carries this instruction prefix. The
#: m2 cross-corpus spike measured it worth ~+0.037 MRR@10, so it is applied by
#: default (override with ``prefix=""`` for the deterministic test fake).
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

#: Default number of ranked owner messages returned / printed.
DEFAULT_LIMIT = 10


@dataclass
class SemanticHit:
    """One ranked search result: an owner message and its best-chunk distance."""

    rank: int
    distance: float
    harness: str
    session_id: str
    message_id: str
    role: str
    text: str


def embed_query(
    query: str, encoder: Encoder, *, prefix: str = QUERY_PREFIX
) -> list[float]:
    """Embed a search ``query`` into a single vector.

    A query is encoded as **one** vector (never chunked — chunking is a
    storage-grain concern for long stored documents; a search query is a single
    point in the embedding space). ``prefix`` defaults to :data:`QUERY_PREFIX`
    (bge's asymmetric query instruction); tests pass ``prefix=""`` so a query
    equal to a stored chunk encodes identically under the deterministic fake.
    """
    return encoder.encode([prefix + query])[0]


def run_semantic_search(
    query: str,
    encoder: Encoder,
    *,
    con: duckdb.DuckDBPyConnection | None = None,
    limit: int = DEFAULT_LIMIT,
    query_prefix: str = QUERY_PREFIX,
    harness: str | None = None,
    role: str | None = None,
) -> list[SemanticHit]:
    """Embed ``query`` and return the ``limit`` nearest owner messages, ranked.

    ``harness`` and ``role`` are optional equality scopes. When either is set,
    only owners matching those equalities are ranked, and the scope applies
    before the cut to ``limit``.

    When ``con`` is ``None`` the warehouse is opened **read-only** through
    ``warehouse.open(read_only=True)`` (and closed on return); tests inject a
    connection. The query is embedded (:func:`embed_query`), then every
    embedding is ranked exactly by cosine distance (:func:`_ranked_hits`): the
    nearest chunk per ``(harness, owner_id)`` is kept (the max-sim owner
    grain), owners are ordered by distance, then harness, then message id, and
    cut to ``limit`` before their ``messages`` rows are read. An embedding
    whose owner row is missing is left out, so the result can then be short;
    it is never an error. No DuckDB extension is needed; m1 embeds messages
    only, so only ``owner_table = 'messages'`` rows participate.
    """
    owns_connection = con is None
    connection = con if con is not None else warehouse.open(read_only=True)
    try:
        query_vector = embed_query(query, encoder, prefix=query_prefix)
        return _ranked_hits(connection, query_vector, limit, harness=harness, role=role)
    finally:
        if owns_connection:
            connection.close()


def _ranked_hits(
    connection: duckdb.DuckDBPyConnection,
    query_vector: list[float],
    limit: int,
    *,
    harness: str | None,
    role: str | None,
) -> list[SemanticHit]:
    """Exact rank of every embedding: nearest chunk per owner, cut, then text.

    One statement serves every scope. Its ranking part reads ``embeddings``
    (plus the ``messages`` key and role columns when ``role`` is set), keeps
    the nearest chunk per ``(harness, owner_id)``, orders by distance, then
    harness, then owner id, and cuts to ``limit``. Only the surviving owners
    are joined to ``messages`` for their text. ``harness`` and ``role`` filter
    before the cut. An embedding whose owner row is missing drops out at the
    final join.
    """
    role_join = ""
    filters = ["e.owner_table = 'messages'"]
    scope_params: list[str] = []
    if harness is not None:
        filters.append("e.harness = ?")
        scope_params.append(harness)
    if role is not None:
        role_join = (
            "JOIN messages s ON s.harness = e.harness AND s.message_id = e.owner_id "
        )
        filters.append("s.role = ?")
        scope_params.append(role)
    rows = connection.execute(
        "WITH ranked AS ("
        "SELECT e.harness, e.owner_id, "
        f"min(array_cosine_distance(e.vector, ?::FLOAT[{EMBED_DIM}])) AS distance "
        f"FROM embeddings e {role_join}"
        f"WHERE {' AND '.join(filters)} "
        "GROUP BY e.harness, e.owner_id "
        "ORDER BY distance, e.harness, e.owner_id "
        f"LIMIT {int(limit)}"
        ") "
        "SELECT w.harness, w.owner_id, m.session_id, m.role, m.text, w.distance "
        "FROM ranked w "
        "JOIN messages m ON m.harness = w.harness AND m.message_id = w.owner_id "
        "ORDER BY w.distance, w.harness, w.owner_id",
        [query_vector, *scope_params],
    ).fetchall()
    return [
        SemanticHit(
            rank=rank,
            distance=distance_value,
            harness=row_harness,
            session_id=session_id,
            message_id=message_id,
            role=row_role,
            text=text,
        )
        for rank, (
            row_harness,
            message_id,
            session_id,
            row_role,
            text,
            distance_value,
        ) in enumerate(rows, start=1)
    ]


def _build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for ``python -m stockroom.semantic``."""
    parser = argparse.ArgumentParser(
        prog="python -m stockroom.semantic",
        description="Pure vector (semantic) search over the stockroom warehouse.",
    )
    parser.add_argument("query", help="The natural-language search query.")
    parser.add_argument(
        "-k",
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help=f"Maximum ranked results to return (default {DEFAULT_LIMIT}).",
    )
    parser.add_argument(
        "--format",
        choices=OUTPUT_FORMATS,
        default=DEFAULT_FORMAT,
        help=(
            "Output shape: 'tsv' (default, header + tab-separated rows, no count "
            "trailer — stream-friendly for LLMs and unix pipes), 'json' (a single "
            "{results: [...]} object), or 'table' (human-readable pretty-print)."
        ),
    )
    parser.add_argument(
        "--harness",
        default=None,
        help=(
            "Rank only this harness (exact string, for example 'cursor' or "
            "'claude'). Omit to search every harness. An unknown value is an "
            "empty result."
        ),
    )
    parser.add_argument(
        "--role",
        choices=("user", "assistant"),
        default=None,
        help=(
            "Rank only this speaker role: 'user' or 'assistant'. Omit to search both."
        ),
    )
    parser.add_argument(
        "--detail",
        choices=DETAIL_LEVELS,
        default=DEFAULT_DETAIL,
        help=(
            "Read-time preview detail: 'compact' (terse), 'snippet' (default, "
            "context-safe), 'full' (untruncated, single-line), or 'raw' "
            "(untruncated, exact whitespace — prefer with --format json). "
            "The preview is elided with a marker reporting how many characters "
            "were hidden; full text always stays whole in the warehouse."
        ),
    )
    return parser


def main(
    argv: list[str] | None = None,
    *,
    encoder_factory: Callable[[], Encoder] = BgeEncoder,
    healer: Callable[[Path], EnsureReport] | None = None,
) -> int:
    """Parse args, search read-only, print a ranked table, return an exit code.

    Returns ``0`` on success, ``1`` when no warehouse exists yet (with a clean
    "run ingest first" hint) or when the encoder cannot be constructed, and
    ``2`` on a bad request (empty query or a non-positive ``--limit``). A
    missing torch with a usable freeze is restored once and the search
    retried. Any other construction failure prints one stderr line naming
    ``sr-initialize``. Both the request validation and the friendly
    missing-warehouse check happen **before** the encoder is constructed, so
    neither error path needs torch. The encoder is built via ``encoder_factory``
    (default :class:`BgeEncoder`, which loads torch out of band; tests inject a
    fake), and the search opens the warehouse read-only.
    """
    args = _build_parser().parse_args(argv)

    if not args.query.strip():
        print(
            "error: empty query (pass the search text as an argument)",
            file=sys.stderr,
        )
        return 2
    if args.limit <= 0:
        print("error: --limit must be a positive integer", file=sys.stderr)
        return 2

    warehouse_file = warehouse.warehouse_path()
    if not warehouse_file.is_file():
        print(
            f"error: no warehouse found at {warehouse_file} — "
            "run `stockroom ingest` first",
            file=sys.stderr,
        )
        return 1

    encoder = start_encoder(encoder_factory, healer=healer)
    if encoder is None:
        return 1
    hits = run_semantic_search(
        args.query,
        encoder,
        limit=args.limit,
        harness=args.harness,
        role=args.role,
    )
    print(render.format_semantic(hits, fmt=args.format, detail=args.detail))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
