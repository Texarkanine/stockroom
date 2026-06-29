"""Tests for the semantic search read surface (``stockroom.semantic``).

Mirrors ``test_embed`` / ``test_query``: a torch-free core exercised against the
deterministic ``FakeEncoder`` (shared from ``conftest``) and the in-memory
``migrated_con`` / env-pointed ``warehouse_home`` fixtures, plus a single
``importorskip("torch")``-gated real-model end-to-end. In-process CLI tests call
``main(..., encoder_factory=FakeEncoder)`` (the ``embed`` precedent) rather than
a subprocess.
"""

from pathlib import Path

import pytest

from conftest import FakeEncoder
from stockroom import embed, semantic, truncate, warehouse


class SpyEncoder:
    """Records the exact strings handed to ``encode`` (to assert prefixing)."""

    def __init__(self) -> None:
        self.seen: list[str] = []

    def encode(self, texts: list[str]) -> list[list[float]]:
        self.seen.extend(texts)
        return [[0.0] * embed.EMBED_DIM for _ in texts]


def _insert_message(
    con,
    *,
    harness: str = "claude",
    session_id: str = "s1",
    ordinal: int = 0,
    role: str = "user",
    text: str | None = "hello world",
) -> str:
    """Insert one minimal ``messages`` row; return its ``message_id``."""
    message_id = f"{session_id}#{ordinal}"
    con.execute(
        "INSERT INTO messages (harness, session_id, message_id, ordinal, role, text) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        [harness, session_id, message_id, ordinal, role, text],
    )
    return message_id


# --- Step 2: embed_query + QUERY_PREFIX -------------------------------------


def test_embed_query_applies_query_prefix_by_default() -> None:
    """``embed_query`` prepends the bge query instruction before encoding."""
    spy = SpyEncoder()
    semantic.embed_query("how do I open the warehouse", spy)
    assert spy.seen == [semantic.QUERY_PREFIX + "how do I open the warehouse"]


def test_embed_query_prefix_can_be_overridden() -> None:
    """An explicit ``prefix=""`` encodes the bare query (the deterministic-fake path)."""
    spy = SpyEncoder()
    semantic.embed_query("bare query", spy, prefix="")
    assert spy.seen == ["bare query"]


def test_embed_query_returns_single_vector() -> None:
    """A query encodes to exactly one ``EMBED_DIM``-length vector (never chunked)."""
    vector = semantic.embed_query("a short question", FakeEncoder())
    assert len(vector) == embed.EMBED_DIM
    assert all(isinstance(component, float) for component in vector)


# --- Step 3: run_semantic_search (KNN + dedup + owner join) -----------------


def test_search_returns_nearest_message_first(migrated_con) -> None:
    """The message whose text the query matches is rank 1 with ~zero distance."""
    _insert_message(migrated_con, ordinal=0, text="alpha topic about cats")
    target_id = _insert_message(migrated_con, ordinal=1, text="beta subject about dogs")
    _insert_message(migrated_con, ordinal=2, text="gamma matter about birds")
    embed.embed_pending(migrated_con, FakeEncoder())

    hits = semantic.run_semantic_search(
        "beta subject about dogs", FakeEncoder(), con=migrated_con, query_prefix=""
    )

    assert hits[0].message_id == target_id
    assert hits[0].rank == 1
    assert hits[0].distance == pytest.approx(0.0, abs=1e-6)


def test_search_ranks_and_distances_ascending(migrated_con) -> None:
    """Hits are ranked 1..n in nondecreasing cosine distance."""
    for ordinal in range(4):
        _insert_message(
            migrated_con, ordinal=ordinal, text=f"distinct message {ordinal}"
        )
    embed.embed_pending(migrated_con, FakeEncoder())

    hits = semantic.run_semantic_search(
        "distinct message 2", FakeEncoder(), con=migrated_con, query_prefix=""
    )

    assert [hit.rank for hit in hits] == list(range(1, len(hits) + 1))
    distances = [hit.distance for hit in hits]
    assert distances == sorted(distances)


def test_search_dedups_multichunk_owner_to_one_row(migrated_con) -> None:
    """A multi-chunk message appears exactly once (its nearest chunk), not per-chunk."""
    long_text = "y" * 3000  # > CHUNK_SIZE -> multiple chunks
    assert len(embed.chunk_text(long_text)) > 1  # guard: really multi-chunk
    long_id = _insert_message(migrated_con, ordinal=0, text=long_text)
    _insert_message(migrated_con, ordinal=1, text="a short other message")
    embed.embed_pending(migrated_con, FakeEncoder())

    hits = semantic.run_semantic_search(
        "anything", FakeEncoder(), con=migrated_con, query_prefix=""
    )

    owners = [hit.message_id for hit in hits]
    assert owners.count(long_id) == 1
    assert len(owners) == len(set(owners))


def test_search_respects_limit(migrated_con) -> None:
    """``limit`` caps the result count; a limit above the corpus returns all."""
    for ordinal in range(7):
        _insert_message(migrated_con, ordinal=ordinal, text=f"message number {ordinal}")
    embed.embed_pending(migrated_con, FakeEncoder())

    capped = semantic.run_semantic_search(
        "message number 3", FakeEncoder(), con=migrated_con, limit=3, query_prefix=""
    )
    assert len(capped) == 3

    everything = semantic.run_semantic_search(
        "message number 3", FakeEncoder(), con=migrated_con, limit=100, query_prefix=""
    )
    assert len(everything) == 7


def test_search_hit_carries_owner_join_fields(migrated_con) -> None:
    """Each hit carries the joined ``messages`` columns (harness/session/role/text)."""
    message_id = _insert_message(
        migrated_con,
        harness="cursor",
        session_id="conv-x",
        ordinal=0,
        role="assistant",
        text="the warehouse opens read only",
    )
    embed.embed_pending(migrated_con, FakeEncoder())

    [hit] = semantic.run_semantic_search(
        "the warehouse opens read only",
        FakeEncoder(),
        con=migrated_con,
        query_prefix="",
    )

    assert hit.harness == "cursor"
    assert hit.session_id == "conv-x"
    assert hit.message_id == message_id
    assert hit.role == "assistant"
    assert hit.text == "the warehouse opens read only"


def test_search_no_embeddings_returns_empty(migrated_con) -> None:
    """A warehouse with messages but no embeddings yields no hits (no error)."""
    _insert_message(migrated_con, ordinal=0, text="never embedded")

    hits = semantic.run_semantic_search(
        "anything", FakeEncoder(), con=migrated_con, query_prefix=""
    )

    assert hits == []


def test_search_owns_connection_opens_read_only(warehouse_home: Path) -> None:
    """With no ``con``, search opens the warehouse itself (read-only) and returns hits."""
    writer = warehouse.open(read_only=False)
    try:
        _insert_message(writer, ordinal=0, text="seeded for the owns-connection path")
        embed.embed_pending(writer, FakeEncoder())
    finally:
        writer.close()

    hits = semantic.run_semantic_search(
        "seeded for the owns-connection path", FakeEncoder(), query_prefix=""
    )

    assert len(hits) == 1
    assert hits[0].text == "seeded for the owns-connection path"


# --- Step 4: _format_hits + CLI ---------------------------------------------


def _never_built() -> FakeEncoder:
    """An ``encoder_factory`` that fails if called (proves the no-torch paths)."""
    raise AssertionError("encoder must not be constructed on this path")


def test_format_hits_shows_similarity_score() -> None:
    """The rendered table reports a similarity ``score`` = ``1 - distance``."""
    hit = semantic.SemanticHit(
        rank=1,
        distance=0.0,
        harness="claude",
        session_id="s1",
        message_id="s1#0",
        role="user",
        text="hello",
    )
    out = semantic._format_hits([hit])
    assert "score" in out.lower()
    assert "1.0" in out  # 1 - 0.0


def test_format_hits_previews_text_single_line() -> None:
    """A long, multi-line ``text`` is previewed truncated onto a single line."""
    hit = semantic.SemanticHit(
        rank=1,
        distance=0.1,
        harness="claude",
        session_id="s1",
        message_id="s1#0",
        role="user",
        text="first line\nsecond line " + "z" * 500,
    )
    out = semantic._format_hits([hit])
    # The preview row is a single physical line (no embedded newline from text).
    assert "first line second line" in out
    assert "z" * 500 not in out  # truncated


def test_format_hits_full_detail_keeps_whole_text() -> None:
    """``detail="full"`` renders the entire message text (no elision marker)."""
    hit = semantic.SemanticHit(
        rank=1,
        distance=0.1,
        harness="claude",
        session_id="s1",
        message_id="s1#0",
        role="user",
        text="z" * 500,
    )
    out = semantic._format_hits([hit], detail="full")
    assert "z" * 500 in out
    assert truncate.ELISION not in out


def test_format_hits_empty_is_zero_results() -> None:
    """No hits renders a ``(0 results)`` trailer rather than an empty string."""
    assert "0 results" in semantic._format_hits([])


def test_cli_prints_ranked_results(warehouse_home: Path, capsys) -> None:
    """The CLI embeds the query with the injected fake and prints the match."""
    writer = warehouse.open(read_only=False)
    try:
        _insert_message(writer, ordinal=0, text="the unique findable phrase")
        embed.embed_pending(writer, FakeEncoder())
    finally:
        writer.close()

    code = semantic.main(["the unique findable phrase"], encoder_factory=FakeEncoder)

    assert code == 0
    out = capsys.readouterr().out
    assert "the unique findable phrase" in out
    assert "(1 result)" in out


def test_cli_limit_flag_caps_results(warehouse_home: Path, capsys) -> None:
    """``-k N`` caps the number of printed result rows."""
    writer = warehouse.open(read_only=False)
    try:
        for ordinal in range(5):
            _insert_message(writer, ordinal=ordinal, text=f"findable message {ordinal}")
        embed.embed_pending(writer, FakeEncoder())
    finally:
        writer.close()

    code = semantic.main(["-k", "2", "findable message"], encoder_factory=FakeEncoder)

    assert code == 0
    assert "(2 results)" in capsys.readouterr().out


def test_cli_detail_full_prints_whole_text(warehouse_home: Path, capsys) -> None:
    """``--detail full`` renders the entire (long) message text; the default elides it."""
    long_text = "the unique findable phrase " + "w" * 400
    writer = warehouse.open(read_only=False)
    try:
        _insert_message(writer, ordinal=0, text=long_text)
        embed.embed_pending(writer, FakeEncoder())
    finally:
        writer.close()

    code = semantic.main(
        ["--detail", "full", "the unique findable phrase"], encoder_factory=FakeEncoder
    )
    assert code == 0
    full_out = capsys.readouterr().out
    assert "w" * 400 in full_out

    default_code = semantic.main(
        ["the unique findable phrase"], encoder_factory=FakeEncoder
    )
    assert default_code == 0
    default_out = capsys.readouterr().out
    assert "w" * 400 not in default_out
    assert truncate.ELISION in default_out


def test_cli_missing_warehouse_is_friendly(warehouse_home: Path, capsys) -> None:
    """No warehouse → exit 1 with a 'run ingest' hint, encoder never constructed."""
    code = semantic.main(["a query"], encoder_factory=_never_built)
    assert code == 1
    assert "ingest" in capsys.readouterr().err.lower()


def test_cli_empty_query_rejected(warehouse_home: Path, capsys) -> None:
    """An empty / whitespace-only query exits 2 and never builds the encoder."""
    code = semantic.main(["   "], encoder_factory=_never_built)
    assert code == 2
    assert capsys.readouterr().err.strip() != ""


def test_cli_nonpositive_limit_rejected(warehouse_home: Path, capsys) -> None:
    """A non-positive ``--limit`` exits 2 with a message and never builds the encoder."""
    code = semantic.main(["-k", "0", "a query"], encoder_factory=_never_built)
    assert code == 2
    assert capsys.readouterr().err.strip() != ""


# --- Step 5: real-model end-to-end (torch-gated, CI-skipped) ----------------


def test_real_model_search_ranks_paraphrase_first(migrated_con) -> None:
    """End-to-end with the real ``BgeEncoder``: a paraphrase finds its message.

    Embeds three clearly distinct-topic messages (no prefix — the passage side)
    and searches a paraphrase of one using the default query prefix (the
    asymmetric query side). The semantically matching message must rank first —
    proving the m1 passage embeddings and the m2 prefixed query embedding land
    in the same space. Torch-gated: skipped under torch-free CI.
    """
    pytest.importorskip("torch")

    _insert_message(
        migrated_con, ordinal=0, text="How do I cook pasta with tomato sauce?"
    )
    dog_id = _insert_message(
        migrated_con, ordinal=1, text="My dog loves to run and play fetch at the park."
    )
    _insert_message(
        migrated_con, ordinal=2, text="The stock market fell and investors lost money."
    )
    encoder = embed.BgeEncoder()
    embed.embed_pending(migrated_con, encoder)

    hits = semantic.run_semantic_search(
        "a puppy enjoys playing fetch outdoors", encoder, con=migrated_con
    )

    assert hits[0].message_id == dog_id
