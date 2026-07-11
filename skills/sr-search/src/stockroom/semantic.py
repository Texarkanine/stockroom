"""CLI + library: pure vector search over the warehouse (``python -m stockroom.semantic``).

The Phase-2 milestone-2 read surface. It embeds a natural-language query with the
same ``sentence-transformers`` model the m1 pipeline used, runs **cosine KNN over
the ``0003`` HNSW index**, dedups multi-chunk hits to one row per owner message
(the "max-sim" obligation m1 deferred), joins the winners back to their
``messages`` rows, and prints a ranked table — all **read-only** through the
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

import duckdb

from stockroom import render, warehouse
from stockroom.embed import EMBED_DIM, BgeEncoder, Encoder
from stockroom.render import DEFAULT_FORMAT, OUTPUT_FORMATS
from stockroom.truncate import DEFAULT_DETAIL, DETAIL_LEVELS

#: bge-small-en-v1.5 is an *asymmetric* retrieval model: passages are embedded
#: with no prefix (m1), but the **query** carries this instruction prefix. The
#: m2 cross-corpus spike measured it worth ~+0.037 MRR@10, so it is applied by
#: default (override with ``prefix=""`` for the deterministic test fake).
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

#: Default number of ranked owner messages returned / printed.
DEFAULT_LIMIT = 10

#: Over-fetch factor for the index KNN before owner dedup. m1 stores one vector
#: per chunk, so a single owner can occupy several of the nearest chunk hits;
#: fetching ``limit * OVERFETCH`` chunk hits before deduping to one row per owner
#: makes it vanishingly unlikely a distinct owner is starved by a multi-chunk
#: neighbour at m2 corpus sizes. (Max-sim dedup is the obligation m1 deferred.)
OVERFETCH = 10


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
) -> list[SemanticHit]:
    """Embed ``query`` and return the ``limit`` nearest owner messages, ranked.

    When ``con`` is ``None`` the warehouse is opened **read-only** through
    ``warehouse.open(read_only=True)`` (and closed on return); tests inject a
    connection. The query is embedded (:func:`embed_query`), then a cosine KNN
    over the ``0003`` HNSW index fetches the nearest ``limit * OVERFETCH`` chunk
    rows; those are deduped to the nearest chunk per ``(harness, owner_id)``
    (preserving ascending distance — the max-sim owner grain), truncated to
    ``limit``, and joined back to their ``messages`` rows. Assumes ``vss`` is
    loaded (the chokepoint's ``ensure_vss``); m1 embeds messages only, so only
    ``owner_table = 'messages'`` rows participate.
    """
    owns_connection = con is None
    connection = con if con is not None else warehouse.open(read_only=True)
    try:
        query_vector = embed_query(query, encoder, prefix=query_prefix)
        fetch_n = limit * OVERFETCH
        chunk_hits = connection.execute(
            "SELECT harness, owner_id, "
            f"array_cosine_distance(vector, ?::FLOAT[{EMBED_DIM}]) AS distance "
            "FROM embeddings WHERE owner_table = 'messages' "
            f"ORDER BY distance LIMIT {fetch_n}",
            [query_vector],
        ).fetchall()

        # Dedup to the nearest chunk per owner. The hits are already in ascending
        # distance order, so the first time an owner is seen is its best chunk.
        best_distance: dict[tuple[str, str], float] = {}
        for harness, owner_id, distance in chunk_hits:
            best_distance.setdefault((harness, owner_id), distance)
        winners = list(best_distance)[:limit]
        if not winners:
            return []

        placeholders = ", ".join(["(?, ?)"] * len(winners))
        params = [value for key in winners for value in key]
        owner_rows = connection.execute(
            "SELECT harness, message_id, session_id, role, text FROM messages "
            f"WHERE (harness, message_id) IN ({placeholders})",
            params,
        ).fetchall()
        by_key = {
            (harness, message_id): (session_id, role, text)
            for harness, message_id, session_id, role, text in owner_rows
        }

        hits: list[SemanticHit] = []
        for rank, key in enumerate(winners, start=1):
            session_id, role, text = by_key[key]
            harness, message_id = key
            hits.append(
                SemanticHit(
                    rank=rank,
                    distance=best_distance[key],
                    harness=harness,
                    session_id=session_id,
                    message_id=message_id,
                    role=role,
                    text=text,
                )
            )
        return hits
    finally:
        if owns_connection:
            connection.close()


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
) -> int:
    """Parse args, search read-only, print a ranked table, return an exit code.

    Returns ``0`` on success, ``1`` when no warehouse exists yet (with a clean
    "run ingest first" hint), and ``2`` on a bad request (empty query or a
    non-positive ``--limit``). Both the request validation and the friendly
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

    encoder = encoder_factory()
    hits = run_semantic_search(args.query, encoder, limit=args.limit)
    print(render.format_semantic(hits, fmt=args.format, detail=args.detail))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
