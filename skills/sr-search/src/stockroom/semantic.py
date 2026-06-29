"""CLI + library: pure vector search over the warehouse (``python -m stockroom.semantic``).

The Phase-2 milestone-2 read surface. It embeds a natural-language query with the
same ``sentence-transformers`` model the m1 pipeline used, runs **cosine KNN over
the ``0003`` HNSW index**, dedups multi-chunk hits to one row per owner message
(the "max-sim" obligation m1 deferred), joins the winners back to their
``messages`` rows, and prints a ranked table — all **read-only** through the
``warehouse.open()`` chokepoint.

Named ``semantic`` (not ``search``) so a keyword-search seeker doesn't grab it by
mistake: this is *pure* vector search. The blended keyword + semantic entrypoint
with context-aware read-time truncation is the separate m3 ``sr-search`` surface.

It mirrors ``stockroom.query``'s shape — a single runnable module (no
``__main__.py``) with a ``run_*`` library entry and a ``con``/encoder injection
seam — and reuses ``stockroom.embed``'s ``Encoder`` / ``BgeEncoder`` / ``EMBED_*``
so no embedding logic is duplicated::

    python -m stockroom.semantic "how does the warehouse lock work"
    python -m stockroom.semantic -k 5 "incremental re-embed"
"""

import argparse
import sys
from collections.abc import Callable
from dataclasses import dataclass

import duckdb

from stockroom import warehouse
from stockroom.embed import EMBED_DIM, BgeEncoder, Encoder

#: Width (chars) of the single-line ``text`` preview in the rendered table. A
#: *display* preview only — the full text stays whole in the store and in
#: ``SemanticHit.text``. Context-aware read-time truncation is m3's feature.
PREVIEW_CHARS = 80

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
    (bge's asymmetric query instruction); tests pass     ``prefix=""`` so a query
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


def _preview(text: str | None) -> str:
    """Collapse ``text`` to a single line and truncate to :data:`PREVIEW_CHARS`."""
    if text is None:
        return ""
    single_line = " ".join(text.split())
    if len(single_line) <= PREVIEW_CHARS:
        return single_line
    return single_line[: PREVIEW_CHARS - 1] + "…"


def _format_hits(hits: list[SemanticHit]) -> str:
    """Render ranked hits as a column-aligned table with a similarity score.

    ``score`` is cosine *similarity* (``1 - distance``, rounded) — friendlier
    than raw distance for a search surface, computed at display time from the
    canonical :attr:`SemanticHit.distance`. ``preview`` is a single-line,
    truncated view of the message text (display only — see :data:`PREVIEW_CHARS`).
    Always ends with a ``(N results)`` / ``(1 result)`` trailer so the output is
    self-describing, including the empty case.
    """
    columns = ["rank", "score", "harness", "role", "preview"]
    rows = [
        [
            str(hit.rank),
            f"{1.0 - hit.distance:.3f}",
            hit.harness,
            hit.role,
            _preview(hit.text),
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
            "run `python -m stockroom.ingest` first",
            file=sys.stderr,
        )
        return 1

    encoder = encoder_factory()
    hits = run_semantic_search(args.query, encoder, limit=args.limit)
    print(_format_hits(hits))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
