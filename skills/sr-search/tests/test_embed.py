"""Tests for the embedding pipeline (``stockroom.embed``).

The pipeline is deliberately split into a torch-free core and a torch-gated
real-model edge so the bulk of it runs under torch-free CI (the Phase-0 torch
contract):

* :func:`chunk_text` — a pure stdlib sliding-window chunker (no torch, no DB).
* :func:`embed_chunks` / :func:`embed_pending` — exercised against a deterministic
  ``FakeEncoder`` and the in-memory ``migrated_con`` fixture, so the per-chunk
  write/selection logic is verified without loading a model.
* :class:`BgeEncoder` — the only torch-dependent surface; its test is
  ``pytest.importorskip("torch")``-gated and skipped in CI.
"""

from pathlib import Path

import duckdb
import pytest

from conftest import FakeEncoder
from stockroom import embed, warehouse


def _insert_message(
    con: duckdb.DuckDBPyConnection,
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


# --- Unit: _pending_chunk_rows (pure flatten, no DuckDB) --------------------


def test_pending_chunk_rows_empty_selection() -> None:
    """An empty selected-message list yields no chunk rows."""
    assert embed._pending_chunk_rows([]) == []


def test_pending_chunk_rows_one_short_message() -> None:
    """One short message yields a single row at chunk_index 0 with verbatim text."""
    text = "hello world"
    rows = embed._pending_chunk_rows([("claude", "s1#0", text)])
    assert rows == [("claude", "s1#0", 0, text)]


def test_pending_chunk_rows_one_long_message() -> None:
    """One long message yields N rows with ascending chunk_index matching chunk_text."""
    text = "y" * 3000
    chunks = embed.chunk_text(text)
    assert len(chunks) > 1
    rows = embed._pending_chunk_rows([("cursor", "s2#1", text)])
    assert rows == [
        ("cursor", "s2#1", index, chunk) for index, chunk in enumerate(chunks)
    ]


def test_pending_chunk_rows_mixed_messages_preserve_owners() -> None:
    """Mixed messages keep (harness, owner_id) boundaries across chunk rows."""
    short = "alpha"
    long_text = "z" * 3000
    long_chunks = embed.chunk_text(long_text)
    rows = embed._pending_chunk_rows(
        [
            ("claude", "a#0", short),
            ("claude", "a#1", "   "),
            ("cursor", "b#0", long_text),
            ("claude", "a#2", None),
        ]
    )
    assert rows[0] == ("claude", "a#0", 0, short)
    assert rows[1:] == [
        ("cursor", "b#0", index, chunk) for index, chunk in enumerate(long_chunks)
    ]


# --- Step 1: chunk_text (pure stdlib sliding window) ------------------------


def test_chunk_short_text_single_chunk() -> None:
    """Text at or under the size threshold is returned as a single, verbatim chunk."""
    text = "a short message"
    chunks = embed.chunk_text(text, size=1200, overlap=150)
    assert chunks == [text]


def test_chunk_empty_is_no_chunks() -> None:
    """Empty or whitespace-only text yields no chunks (caller skips embedding)."""
    assert embed.chunk_text("", size=1200, overlap=150) == []
    assert embed.chunk_text("   \n\t  ", size=1200, overlap=150) == []
    assert embed.chunk_text(None, size=1200, overlap=150) == []


def test_chunk_long_text_overlapping() -> None:
    """Long text splits into overlapping windows with complete, ordered coverage.

    Each chunk stays within ``size`` chars; consecutive chunks advance by
    ``size - overlap`` and share an ``overlap``-char suffix/prefix; the chunk
    sequence is deterministic and reconstructs the source when de-overlapped.
    """
    size, overlap = 100, 20
    text = "".join(chr(ord("a") + (i % 26)) for i in range(450))

    chunks = embed.chunk_text(text, size=size, overlap=overlap)

    assert len(chunks) > 1
    assert all(len(c) <= size for c in chunks)
    # Deterministic.
    assert embed.chunk_text(text, size=size, overlap=overlap) == chunks
    # Consecutive chunks overlap by exactly `overlap` chars.
    step = size - overlap
    for index in range(len(chunks) - 1):
        prev, nxt = chunks[index], chunks[index + 1]
        assert prev[step:] == nxt[: len(prev) - step]
    # De-overlapped concatenation reconstructs the whole source (no gaps).
    reconstructed = chunks[0] + "".join(c[overlap:] for c in chunks[1:])
    assert reconstructed == text


# --- Step 2: embed_chunks + embed_pending (injected encoder, torch-free) ----


def test_embed_chunks_one_vector_per_chunk() -> None:
    """``embed_chunks`` returns one ``EMBED_DIM`` vector per chunk, in order."""
    long_text = "x" * 3000  # > CHUNK_SIZE -> multiple chunks
    expected_chunks = embed.chunk_text(long_text)
    assert len(expected_chunks) > 1  # guard: the fixture really is multi-chunk

    vectors = embed.embed_chunks(long_text, FakeEncoder())

    assert len(vectors) == len(expected_chunks)
    assert all(len(v) == embed.EMBED_DIM for v in vectors)
    # In chunk order: each vector matches its chunk's deterministic encoding.
    assert vectors == [FakeEncoder._vector(c) for c in expected_chunks]


def test_embed_chunks_empty_text_no_vectors() -> None:
    """Whitespace-only text produces no vectors (nothing to embed)."""
    assert embed.embed_chunks("   ", FakeEncoder()) == []


def test_embed_pending_writes_per_chunk_rows(
    migrated_con: duckdb.DuckDBPyConnection,
) -> None:
    """A single-chunk message writes 1 row; a multi-chunk message writes N rows.

    Rows carry ``owner_table='messages'``, ``owner_id=message_id``, ascending
    ``chunk_index`` 0..N-1, the current model, and a 384-vector. ``tool_calls``
    are never an owner in m1.
    """
    short_id = _insert_message(migrated_con, ordinal=0, text="short message")
    long_id = _insert_message(migrated_con, ordinal=1, text="y" * 3000)
    n_long = len(embed.chunk_text("y" * 3000))

    written = embed.embed_pending(migrated_con, FakeEncoder())

    assert written == 1 + n_long
    short_rows = migrated_con.execute(
        "SELECT chunk_index, embed_model, len(vector) FROM embeddings "
        "WHERE owner_id = ? ORDER BY chunk_index",
        [short_id],
    ).fetchall()
    assert short_rows == [(0, embed.EMBED_MODEL, embed.EMBED_DIM)]
    long_indices = migrated_con.execute(
        "SELECT chunk_index FROM embeddings WHERE owner_id = ? ORDER BY chunk_index",
        [long_id],
    ).fetchall()
    assert [r[0] for r in long_indices] == list(range(n_long))
    # All rows are owned by messages; tool_calls is never embedded in m1.
    owner_tables = migrated_con.execute(
        "SELECT DISTINCT owner_table FROM embeddings"
    ).fetchall()
    assert owner_tables == [("messages",)]


def test_embed_pending_incremental_is_no_op_then_embeds_new(
    migrated_con: duckdb.DuckDBPyConnection,
) -> None:
    """A second run with no new content writes nothing; a new message embeds only it."""
    _insert_message(migrated_con, ordinal=0, text="first")
    first = embed.embed_pending(migrated_con, FakeEncoder())
    assert first == 1

    again = embed.embed_pending(migrated_con, FakeEncoder())
    assert again == 0
    assert migrated_con.execute("SELECT count(*) FROM embeddings").fetchone()[0] == 1

    new_id = _insert_message(migrated_con, ordinal=1, text="second")
    third = embed.embed_pending(migrated_con, FakeEncoder())
    assert third == 1
    embedded_owners = migrated_con.execute(
        "SELECT count(*) FROM embeddings WHERE owner_id = ?", [new_id]
    ).fetchone()[0]
    assert embedded_owners == 1
    assert migrated_con.execute("SELECT count(*) FROM embeddings").fetchone()[0] == 2


def test_embed_pending_skips_empty_text(
    migrated_con: duckdb.DuckDBPyConnection,
) -> None:
    """Messages with NULL or whitespace-only text get no embedding row."""
    _insert_message(migrated_con, ordinal=0, text=None)
    _insert_message(migrated_con, ordinal=1, text="    \n  ")

    written = embed.embed_pending(migrated_con, FakeEncoder())

    assert written == 0
    assert migrated_con.execute("SELECT count(*) FROM embeddings").fetchone()[0] == 0


def test_embed_pending_is_model_aware(
    migrated_con: duckdb.DuckDBPyConnection,
) -> None:
    """A vector under a different model is re-embedded under (and replaced by) the
    current model.

    The owner is selected (it lacks a *current-model* row), and because the
    ``embeddings`` PK excludes ``embed_model``, the prior model's rows are
    replaced rather than coexisting at the same ``chunk_index``.
    """
    message_id = _insert_message(migrated_con, ordinal=0, text="content")
    # Pre-seed a row under a *different* model.
    migrated_con.execute(
        "INSERT INTO embeddings "
        "(harness, owner_table, owner_id, chunk_index, embed_model, vector) "
        "VALUES ('claude', 'messages', ?, 0, 'old-model', ?)",
        [message_id, [0.0] * embed.EMBED_DIM],
    )

    written = embed.embed_pending(migrated_con, FakeEncoder())

    assert written == 1  # re-embedded under the current model
    models = {
        r[0]
        for r in migrated_con.execute(
            "SELECT DISTINCT embed_model FROM embeddings WHERE owner_id = ?",
            [message_id],
        ).fetchall()
    }
    assert models == {embed.EMBED_MODEL}


def test_embed_pending_knn_nearest_chunk_is_expected(
    migrated_con: duckdb.DuckDBPyConnection,
) -> None:
    """The cosine-nearest stored vector to a chunk's encoding is that chunk's row."""
    _insert_message(migrated_con, ordinal=0, text="alpha topic")
    target_id = _insert_message(migrated_con, ordinal=1, text="beta subject")
    _insert_message(migrated_con, ordinal=2, text="gamma matter")
    embed.embed_pending(migrated_con, FakeEncoder())

    query = FakeEncoder._vector("beta subject")
    nearest = migrated_con.execute(
        "SELECT owner_id FROM embeddings "
        "ORDER BY array_cosine_distance(vector, ?::FLOAT[384]) LIMIT 1",
        [query],
    ).fetchone()[0]
    assert nearest == target_id


# --- Unit: cross-message batch encode ---------------------------------------


class _RecordingEncoder:
    """FakeEncoder that records each ``encode`` call's batch size."""

    def __init__(self) -> None:
        self.calls: list[int] = []
        self._inner = FakeEncoder()

    def encode(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(len(texts))
        return self._inner.encode(texts)


def test_embed_pending_batches_across_messages(
    migrated_con: duckdb.DuckDBPyConnection,
) -> None:
    """Multiple single-chunk pending messages are encoded in one cross-message batch."""
    for ordinal, text in enumerate(("alpha", "beta", "gamma")):
        _insert_message(migrated_con, ordinal=ordinal, text=text)
    recorder = _RecordingEncoder()

    written = embed.embed_pending(migrated_con, recorder)

    assert written == 3
    assert recorder.calls == [3]
    assert max(recorder.calls) <= embed.EMBED_BATCH_SIZE


def test_embed_pending_batched_vectors_match_single_encode(
    migrated_con: duckdb.DuckDBPyConnection,
) -> None:
    """Stored vectors equal FakeEncoder singles for each chunk (exact identity)."""
    short_id = _insert_message(migrated_con, ordinal=0, text="short message")
    long_text = "y" * 3000
    long_id = _insert_message(migrated_con, ordinal=1, text=long_text)
    chunks = embed.chunk_text(long_text)

    written = embed.embed_pending(migrated_con, FakeEncoder())

    assert written == 1 + len(chunks)
    short_vec = migrated_con.execute(
        "SELECT vector FROM embeddings WHERE owner_id = ? AND chunk_index = 0",
        [short_id],
    ).fetchone()[0]
    # DuckDB FLOAT[384] round-trips as float32; compare in that precision.
    assert list(short_vec) == pytest.approx(
        FakeEncoder._vector("short message"), abs=1e-6
    )
    for index, chunk in enumerate(chunks):
        stored = migrated_con.execute(
            "SELECT vector FROM embeddings WHERE owner_id = ? AND chunk_index = ?",
            [long_id, index],
        ).fetchone()[0]
        assert list(stored) == pytest.approx(FakeEncoder._vector(chunk), abs=1e-6)


# --- Unit: orphan embedding cleanup -----------------------------------------


def _insert_embedding(
    con: duckdb.DuckDBPyConnection,
    *,
    harness: str,
    owner_id: str,
    embed_model: str = embed.EMBED_MODEL,
    chunk_index: int = 0,
) -> None:
    """Insert one embeddings row (does not require a matching messages row)."""
    con.execute(
        "INSERT INTO embeddings "
        "(harness, owner_table, owner_id, chunk_index, embed_model, vector) "
        "VALUES (?, 'messages', ?, ?, ?, ?)",
        [harness, owner_id, chunk_index, embed_model, [0.0] * embed.EMBED_DIM],
    )


def test_embed_pending_removes_orphaned_embeddings(
    migrated_con: duckdb.DuckDBPyConnection,
) -> None:
    """Embedding rows whose owner_id is missing from messages are deleted."""
    _insert_embedding(migrated_con, harness="claude", owner_id="gone#0")
    _insert_embedding(migrated_con, harness="claude", owner_id="gone#0", chunk_index=1)

    written = embed.embed_pending(migrated_con, FakeEncoder())

    assert written == 0
    assert (
        migrated_con.execute(
            "SELECT count(*) FROM embeddings WHERE owner_id = 'gone#0'"
        ).fetchone()[0]
        == 0
    )


def test_embed_pending_orphan_cleanup_preserves_valid_and_other_sessions(
    migrated_con: duckdb.DuckDBPyConnection,
) -> None:
    """Valid embeddings (including other sessions) survive orphan cleanup."""
    keep_id = _insert_message(migrated_con, session_id="keep", ordinal=0, text="stay")
    other_id = _insert_message(
        migrated_con, harness="cursor", session_id="other", ordinal=0, text="other"
    )
    embed.embed_pending(migrated_con, FakeEncoder())
    _insert_embedding(migrated_con, harness="claude", owner_id="orphan#0")

    written = embed.embed_pending(migrated_con, FakeEncoder())

    assert written == 0
    owners = {
        r[0]
        for r in migrated_con.execute(
            "SELECT DISTINCT owner_id FROM embeddings"
        ).fetchall()
    }
    assert owners == {keep_id, other_id}


def test_embed_pending_orphan_cleanup_runs_when_nothing_to_embed(
    migrated_con: duckdb.DuckDBPyConnection,
) -> None:
    """Orphans are swept even when the incremental embed selection is empty."""
    keep_id = _insert_message(migrated_con, ordinal=0, text="already")
    embed.embed_pending(migrated_con, FakeEncoder())
    _insert_embedding(migrated_con, harness="claude", owner_id="dangling#0")

    written = embed.embed_pending(migrated_con, FakeEncoder())

    assert written == 0
    assert (
        migrated_con.execute(
            "SELECT count(*) FROM embeddings WHERE owner_id = 'dangling#0'"
        ).fetchone()[0]
        == 0
    )
    assert (
        migrated_con.execute(
            "SELECT count(*) FROM embeddings WHERE owner_id = ?", [keep_id]
        ).fetchone()[0]
        == 1
    )


def test_embed_pending_orphan_cleanup_all_models(
    migrated_con: duckdb.DuckDBPyConnection,
) -> None:
    """Dangling rows under any embed_model are removed, not only the current one."""
    _insert_embedding(
        migrated_con, harness="claude", owner_id="old#0", embed_model="old-model"
    )

    embed.embed_pending(migrated_con, FakeEncoder())

    assert migrated_con.execute("SELECT count(*) FROM embeddings").fetchone()[0] == 0


# --- Step 6: real-model encoder (torch-gated) + CLI -------------------------


def _seed_warehouse_message(text: str = "hi there", ordinal: int = 0) -> None:
    """Open the env-pointed warehouse read-write and insert one message row."""
    con = warehouse.open(read_only=False)
    try:
        con.execute(
            "INSERT INTO messages "
            "(harness, session_id, message_id, ordinal, role, text) "
            "VALUES ('claude', 's1', ?, ?, 'user', ?)",
            [f"s1#{ordinal}", ordinal, text],
        )
    finally:
        con.close()


def test_embed_cli_missing_warehouse_is_friendly(warehouse_home: Path, capsys) -> None:
    """With no warehouse present, the CLI exits nonzero with a 'run ingest' hint
    (and never constructs the torch-backed encoder). The hint names the on-path
    command (`stockroom ingest`), never a raw module invocation — pinned exactly
    so the message cannot drift back."""
    code = embed.main([])
    assert code == 1
    err = capsys.readouterr().err
    assert "run `stockroom ingest` first" in err


def test_embed_cli_embeds_pending_and_reports_count(
    warehouse_home: Path, capsys
) -> None:
    """The CLI embeds pending messages with the injected encoder and prints a count."""
    _seed_warehouse_message("hello world")

    code = embed.main([], encoder_factory=FakeEncoder)

    assert code == 0
    assert "embedded 1" in capsys.readouterr().out
    con = warehouse.open(read_only=True)
    try:
        assert con.execute("SELECT count(*) FROM embeddings").fetchone()[0] == 1
    finally:
        con.close()


def test_embed_cli_full_reembeds(warehouse_home: Path, capsys) -> None:
    """``--full`` re-embeds already-embedded content (incremental would be a no-op)."""
    _seed_warehouse_message("hello world")
    embed.main([], encoder_factory=FakeEncoder)
    capsys.readouterr()  # discard first run's output

    incremental = embed.main([], encoder_factory=FakeEncoder)
    assert incremental == 0
    assert "embedded 0" in capsys.readouterr().out

    full = embed.main(["--full"], encoder_factory=FakeEncoder)
    assert full == 0
    assert "embedded 1" in capsys.readouterr().out
    con = warehouse.open(read_only=True)
    try:
        assert con.execute("SELECT count(*) FROM embeddings").fetchone()[0] == 1
    finally:
        con.close()


def test_embed_pending_on_progress_reports_message_counts(
    migrated_con: duckdb.DuckDBPyConnection,
) -> None:
    """``on_progress`` receives a start line and per-batch chunk progress lines."""
    _insert_message(migrated_con, ordinal=0, text="alpha")
    _insert_message(migrated_con, ordinal=1, text="beta")
    _insert_message(migrated_con, ordinal=2, text="gamma")
    lines: list[str] = []
    written = embed.embed_pending(migrated_con, FakeEncoder(), on_progress=lines.append)
    assert written == 3
    assert lines[0] == "embed: 3 messages (3 chunks)"
    assert lines[1:] == ["embed: 3/3 chunks"]


def test_embed_cli_quiet_default_has_no_mid_run_progress(
    warehouse_home: Path, capsys
) -> None:
    """Without ``--verbose``, stdout is only the final embedded-count line."""
    _seed_warehouse_message("hello world", ordinal=0)
    _seed_warehouse_message("second message", ordinal=1)
    code = embed.main([], encoder_factory=FakeEncoder)
    assert code == 0
    out = capsys.readouterr().out
    lines = [line for line in out.splitlines() if line.strip()]
    assert len(lines) == 1
    assert "embedded 2" in lines[0]
    assert not any("chunks" in line for line in lines)


def test_embed_cli_verbose_prints_progress_and_count(
    warehouse_home: Path, capsys
) -> None:
    """``--verbose`` emits progress lines and still prints the embedded count."""
    _seed_warehouse_message("hello world", ordinal=0)
    _seed_warehouse_message("second message", ordinal=1)
    code = embed.main(["--verbose"], encoder_factory=FakeEncoder)
    assert code == 0
    out = capsys.readouterr().out
    assert "embed: 2 messages (2 chunks)" in out
    assert "embed: 2/2 chunks" in out
    assert "embedded 2" in out


def test_embed_cli_verbose_missing_warehouse_still_friendly(
    warehouse_home: Path, capsys
) -> None:
    """``--verbose`` does not change the missing-warehouse friendly error path."""
    code = embed.main(["--verbose"])
    assert code == 1
    err = capsys.readouterr().err
    assert "run `stockroom ingest` first" in err


def test_bge_encoder_encodes_to_384_on_cpu() -> None:
    """``BgeEncoder`` loads ``bge-small-en-v1.5`` (no ``trust_remote_code``) and
    encodes to 384-dim; a default chunk stays within the 512-token window.

    Torch-gated: skipped under torch-free CI (the Phase-0 contract). A successful
    construction proves the plain BERT arch loads with ``trust_remote_code=False``.
    """
    pytest.importorskip("torch")

    encoder = embed.BgeEncoder()
    vectors = encoder.encode(["a sample sentence to embed"])
    assert len(vectors) == 1
    assert len(vectors[0]) == embed.EMBED_DIM

    # Token-window guard: bge's window is 512 tokens; a worst-case dense-code
    # chunk at the default char size must not silently overflow it.
    assert encoder.model.max_seq_length <= 512
    dense_chunk = embed.chunk_text("def f(x):\n    return x + 1\n" * 200)[0]
    token_ids = encoder.model.tokenizer(dense_chunk)["input_ids"]
    assert len(token_ids) <= 512


def test_bge_encoder_batched_matches_single_within_float32() -> None:
    """Batched ``encode`` matches per-text singles within float32 near-equality.

    sentence-transformers is not bit-identical across batch vs single (padding);
    stockroom's accuracy bar is float32-near equality, not exact identity.
    """
    pytest.importorskip("torch")

    texts = [
        "short alpha",
        "short beta about dogs and cats",
        "x" * 800,
    ]
    encoder = embed.BgeEncoder()
    singles = [encoder.encode([text])[0] for text in texts]
    batched = encoder.encode(texts)
    for single, batch_vec in zip(singles, batched, strict=True):
        assert batch_vec == pytest.approx(single, abs=1e-5)
