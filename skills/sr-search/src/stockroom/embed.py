"""CLI + library: embed message text into the warehouse (``python -m stockroom.embed``).

The Phase-2 milestone-1 embedding pipeline. It reads message text from the
warehouse, splits long text into bounded overlapping chunks, encodes each chunk
into a 384-dim vector with a local ``sentence-transformers`` model, and writes
**one ``embeddings`` row per chunk** (``chunk_index = 0..N-1``) through the
``warehouse.open()`` chokepoint — re-embedding only content that lacks a vector
for the current model.

Design seams (so the bulk runs under torch-free CI, per the Phase-0 contract):

* :func:`chunk_text` is pure stdlib — no torch, no DB.
* :func:`embed_chunks` / :func:`embed_pending` take an injected :class:`Encoder`,
  so the per-chunk write and incremental-selection logic is unit-tested against a
  deterministic fake with no model loaded.
* :class:`BgeEncoder` is the only torch-dependent surface; it lazy-imports
  ``sentence_transformers`` so importing this module never pulls torch.

Storage grain (per-chunk vs mean-pool), owner grain (messages-only), incremental
detection, the VSS/HNSW index, and the model choice are documented in
``memory-bank/active/creative/creative-*.md``.
"""

from typing import Protocol, runtime_checkable

import duckdb

#: The local sentence-transformers model used for message embeddings. Recorded
#: per ``embeddings`` row (``embed_model``) so a future model swap re-embeds only
#: rows lacking the *current* model — see
#: ``creative-embedding-model-selection.md`` (bge-small-en-v1.5 @ 384-dim, no
#: ``trust_remote_code``, MIT, 512-token window, no passage prefix for m1).
EMBED_MODEL = "BAAI/bge-small-en-v1.5"

#: The embedding width. Fixed by the ``0001`` schema (``vector FLOAT[384]``);
#: staying at 384-dim is a hard constraint (a different width needs a migration
#: + full re-embed). Every supported model must emit 384-dim vectors.
EMBED_DIM = 384

#: Default sliding-window chunk size / overlap, in characters. A conservative
#: char proxy for bge's 512-token window (token-aware chunking is the ideal; see
#: ``creative-chunk-storage-grain.md``).
CHUNK_SIZE = 1200
CHUNK_OVERLAP = 150


@runtime_checkable
class Encoder(Protocol):
    """Encodes a batch of strings into embedding vectors.

    The pipeline depends only on this protocol, never on a concrete model, so
    the chunking/selection/write logic is testable with a deterministic fake and
    the real (torch-backed) :class:`BgeEncoder` is an injected, CI-skippable edge.
    """

    def encode(self, texts: list[str]) -> list[list[float]]:
        """Return one ``EMBED_DIM``-length vector per input string, in order."""
        ...


def chunk_text(
    text: str | None, *, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP
) -> list[str]:
    """Split ``text`` into ordered, overlapping windows of at most ``size`` chars.

    A pure-stdlib sliding window: empty/whitespace-only (or ``None``) text yields
    ``[]`` (the caller skips embedding); text at or under ``size`` is returned as
    a single verbatim chunk; longer text is cut into windows of ``size`` chars
    advancing by ``size - overlap``, so consecutive chunks share an
    ``overlap``-char boundary and the windows cover the whole string with no gap.
    Deterministic for a given ``(text, size, overlap)``.
    """
    if text is None or not text.strip():
        return []
    if len(text) <= size:
        return [text]

    step = size - overlap
    chunks: list[str] = []
    start = 0
    while start < len(text):
        chunks.append(text[start : start + size])
        if start + size >= len(text):
            break
        start += step
    return chunks


def embed_chunks(text: str, encoder: Encoder) -> list[list[float]]:
    """Chunk ``text`` and encode each chunk, returning one vector per chunk.

    No pooling: an N-chunk message yields N vectors, in chunk order (the
    per-chunk storage grain — see ``creative-chunk-storage-grain.md``). Empty or
    whitespace-only text yields no vectors.
    """
    chunks = chunk_text(text)
    if not chunks:
        return []
    return encoder.encode(chunks)


def embed_pending(
    con: duckdb.DuckDBPyConnection,
    encoder: Encoder,
    *,
    embed_model: str = EMBED_MODEL,
    full: bool = False,
) -> int:
    """Embed messages lacking a current-model vector; return rows written.

    Selects ``messages`` rows with non-empty ``text`` that have no ``embeddings``
    row for ``embed_model`` (so new content and a model change both re-embed;
    edits are caught by the ingest-writer cascade — see
    ``creative-incremental-reembed-detection.md``). With ``full=True`` the
    "already embedded" filter is dropped and every non-empty message is
    re-embedded (its existing current-model rows are deleted first), mirroring
    ``ingest --full``.

    Each selected message has its existing ``messages`` embedding rows deleted
    (the ``embeddings`` PK excludes ``embed_model``, so a model change *replaces*
    the owner's vectors), then is chunked and encoded, and one row per chunk is
    written: ``(harness, 'messages', message_id, chunk_index, embed_model,
    vector)``. ``tool_calls`` are not embedded in m1. Assumes a read-write
    connection with ``vss`` loaded (the chokepoint's ``ensure_vss``).
    """
    if full:
        selected = con.execute(
            "SELECT harness, message_id, text FROM messages "
            "WHERE text IS NOT NULL AND length(trim(text)) > 0"
        ).fetchall()
    else:
        selected = con.execute(
            "SELECT m.harness, m.message_id, m.text FROM messages m "
            "WHERE m.text IS NOT NULL AND length(trim(m.text)) > 0 "
            "AND NOT EXISTS ("
            "  SELECT 1 FROM embeddings e "
            "  WHERE e.harness = m.harness AND e.owner_table = 'messages' "
            "  AND e.owner_id = m.message_id AND e.embed_model = ?"
            ")",
            [embed_model],
        ).fetchall()

    written = 0
    for harness, message_id, text in selected:
        # Clear any prior vectors for this owner (a model change replaces them;
        # the PK has no embed_model, so coexisting models would collide).
        con.execute(
            "DELETE FROM embeddings WHERE harness = ? AND owner_table = 'messages' "
            "AND owner_id = ?",
            [harness, message_id],
        )
        vectors = embed_chunks(text, encoder)
        for chunk_index, vector in enumerate(vectors):
            con.execute(
                "INSERT INTO embeddings "
                "(harness, owner_table, owner_id, chunk_index, embed_model, vector) "
                "VALUES (?, 'messages', ?, ?, ?, ?)",
                [harness, message_id, chunk_index, embed_model, vector],
            )
            written += 1
    return written
