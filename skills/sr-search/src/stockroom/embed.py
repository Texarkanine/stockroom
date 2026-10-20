"""CLI + library: embed message text into the warehouse (``python -m stockroom.embed``).

The Phase-2 milestone-1 embedding pipeline. It reads message text from the
warehouse, splits long text into bounded overlapping chunks, encodes chunks in
cross-message batches with a local ``sentence-transformers`` model, and writes
**one ``embeddings`` row per chunk** (``chunk_index = 0..N-1``) through the
``warehouse.open()`` chokepoint — re-embedding only content that lacks a vector
for the current model. After the normal sweep it also deletes orphaned
``owner_table='messages'`` embedding rows whose owners no longer exist.

Design seams (so the bulk runs under torch-free CI, per the Phase-0 contract):

* :func:`chunk_text` / :func:`_pending_chunk_rows` are pure stdlib — no torch, no DB.
* :func:`embed_chunks` / :func:`embed_pending` take an injected :class:`Encoder`,
  so the per-chunk write and incremental-selection logic is unit-tested against a
  deterministic fake with no model loaded.
* :class:`BgeEncoder` is the only torch-dependent surface; it lazy-imports
  ``sentence_transformers`` so importing this module never pulls torch.

Storage grain (per-chunk vs mean-pool), owner grain (messages-only), incremental
detection, the VSS/HNSW index, and the model choice are documented in
``memory-bank/active/creative/creative-*.md``.
"""

import argparse
import importlib
import logging
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

import duckdb

from stockroom import warehouse
from stockroom.engine_env import EnsureReport, ensure_engine_env
from stockroom.shim import default_app_dir
from stockroom.torch_source import read_freeze_path

#: Optional progress reporter: one human-readable line per call (CLI wires print).
ProgressCallback = Callable[[str], None]
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

#: Cross-message encode window size. Most messages are a single chunk; batching
#: across owners feeds the accelerator instead of ``encode([one])`` per message.
#: Chosen from CPU measurement (~plateau at 32–128); not a quality knob.
EMBED_BATCH_SIZE = 32


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


def _pending_chunk_rows(
    selected: list[tuple[str, str, str | None]],
) -> list[tuple[str, str, int, str]]:
    """Flatten selected ``(harness, message_id, text)`` rows into chunk records.

    Each non-empty chunk becomes ``(harness, owner_id, chunk_index, chunk_text)``
    with ``chunk_index`` ascending from 0 within that owner, matching
    :func:`chunk_text` windows. Empty/whitespace-only texts contribute nothing.
    Pure stdlib — no encoder, no DuckDB.
    """
    rows: list[tuple[str, str, int, str]] = []
    for harness, message_id, text in selected:
        for chunk_index, chunk in enumerate(chunk_text(text)):
            rows.append((harness, message_id, chunk_index, chunk))
    return rows


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


def _embed_selected_messages(
    con: duckdb.DuckDBPyConnection,
    encoder: Encoder,
    selected: list[tuple[str, str, str | None]],
    *,
    embed_model: str = EMBED_MODEL,
    on_progress: ProgressCallback | None = None,
) -> int:
    """Replace embeddings for ``selected`` messages; return chunk rows written.

    Flattens ``selected`` ``(harness, message_id, text)`` rows into chunk
    records, encodes them in cross-message windows of :data:`EMBED_BATCH_SIZE`,
    and writes one ``embeddings`` row per chunk. Prior vectors for those owners
    are cleared in a set-oriented delete before insert (the ``embeddings`` PK
    excludes ``embed_model``, so a model change *replaces* the owner's vectors).
    The delete and all batch inserts run in one DuckDB transaction so a mid-run
    encode/insert failure rolls back to the pre-replace state.

    Does **not** sweep orphaned embeddings — callers that want warehouse hygiene
    should invoke :func:`_delete_orphan_message_embeddings` separately.
    """
    chunk_rows = _pending_chunk_rows(selected)
    n_chunks = len(chunk_rows)
    if on_progress is not None:
        on_progress(f"embed: {len(selected)} messages ({n_chunks} chunks)")
    if not selected:
        return 0

    owner_keys = list(
        {(harness, message_id) for harness, message_id, _text in selected}
    )
    harnesses = [h for h, _ in owner_keys]
    owner_ids = [oid for _, oid in owner_keys]
    written = 0
    con.execute("BEGIN")
    try:
        con.execute(
            "DELETE FROM embeddings WHERE owner_table = 'messages' "
            "AND (harness, owner_id) IN ("
            "  SELECT UNNEST(?::VARCHAR[]) AS harness, "
            "         UNNEST(?::VARCHAR[]) AS owner_id"
            ")",
            [harnesses, owner_ids],
        )

        for batch_start in range(0, n_chunks, EMBED_BATCH_SIZE):
            batch = chunk_rows[batch_start : batch_start + EMBED_BATCH_SIZE]
            vectors = encoder.encode([chunk for *_meta, chunk in batch])
            insert_rows = [
                (harness, owner_id, chunk_index, embed_model, vector)
                for (harness, owner_id, chunk_index, _chunk), vector in zip(
                    batch, vectors, strict=True
                )
            ]
            con.executemany(
                "INSERT INTO embeddings "
                "(harness, owner_table, owner_id, chunk_index, embed_model, vector) "
                "VALUES (?, 'messages', ?, ?, ?, ?)",
                insert_rows,
            )
            written += len(batch)
            if on_progress is not None:
                on_progress(f"embed: {written}/{n_chunks} chunks")
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
    return written


def _delete_orphan_message_embeddings(
    con: duckdb.DuckDBPyConnection, *, count_rows: bool = True
) -> int:
    """Delete ``owner_table='messages'`` embeddings with no matching messages row.

    Removes dangling owners for **all** ``embed_model`` values. Independent of
    the re-embed sweep — safe to call when nothing is pending.

    When ``count_rows`` is true (default), returns the number of rows deleted via
    ``RETURNING``. When false, runs a plain ``DELETE`` (no Python materialization)
    and returns ``0`` (count unknown).
    """
    delete_sql = (
        "DELETE FROM embeddings WHERE owner_table = 'messages' "
        "AND NOT EXISTS ("
        "  SELECT 1 FROM messages m "
        "  WHERE m.harness = embeddings.harness AND m.message_id = embeddings.owner_id"
        ")"
    )
    if not count_rows:
        con.execute(delete_sql)
        return 0
    orphans = con.execute(delete_sql + " RETURNING 1").fetchall()
    return len(orphans)


def embed_pending(
    con: duckdb.DuckDBPyConnection,
    encoder: Encoder,
    *,
    embed_model: str = EMBED_MODEL,
    full: bool = False,
    on_progress: ProgressCallback | None = None,
) -> int:
    """Embed messages lacking a current-model vector; return rows written.

    Selects ``messages`` rows with non-empty ``text`` that have no ``embeddings``
    row for ``embed_model`` (so new content and a model change both re-embed;
    edits are caught by the ingest-writer cascade — see
    ``creative-incremental-reembed-detection.md``). With ``full=True`` the
    "already embedded" filter is dropped and every non-empty message is
    re-embedded (its existing rows are deleted first), mirroring ``ingest --full``.

    Delegates the encode/write replace path to :func:`_embed_selected_messages`
    and orphan hygiene to :func:`_delete_orphan_message_embeddings` (all models
    for dangling message owners). ``tool_calls`` are not embedded in m1. Assumes
    a read-write connection with ``vss`` loaded (the chokepoint's ``ensure_vss``).

    When ``on_progress`` is set, emits embed progress from the replace helper,
    then ``embed: removed K orphaned embedding rows`` when ``K > 0``.
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

    written = _embed_selected_messages(
        con,
        encoder,
        list(selected),
        embed_model=embed_model,
        on_progress=on_progress,
    )
    removed = _delete_orphan_message_embeddings(con, count_rows=on_progress is not None)
    if on_progress is not None and removed:
        on_progress(f"embed: removed {removed} orphaned embedding rows")

    return written


class _DropUnauthenticatedHubWarning(logging.Filter):
    """Drop the Hub's unauthenticated-request notice and nothing else."""

    def filter(self, record: logging.LogRecord) -> bool:
        return "unauthenticated requests to the HF Hub" not in record.getMessage()


def silence_unauthenticated_hub_warning() -> None:
    """Stop the Hub's unauthenticated-request notice from reaching stderr.

    The Hub sends that text as an ``X-HF-Warning`` response header, and
    ``huggingface_hub`` logs it once per process. Stockroom does not use a
    token for the local embedding model; the notice is not a failure. Other
    warnings from the same logger, including a failed download, still pass.
    Idempotent: a second call does not stack another filter.
    """
    hub = logging.getLogger("huggingface_hub.utils._http")
    if not any(
        isinstance(item, _DropUnauthenticatedHubWarning) for item in hub.filters
    ):
        hub.addFilter(_DropUnauthenticatedHubWarning())


class BgeEncoder:
    """A ``sentence-transformers`` encoder for ``BAAI/bge-small-en-v1.5`` (384-dim).

    The only torch-dependent surface in the pipeline. ``sentence_transformers``
    (and thus torch) is imported lazily on construction, so importing
    :mod:`stockroom.embed` never pulls torch — the chunker and the injected-encoder
    pipeline stay importable and testable under torch-free CI. The device is
    selected at construction (CUDA when available, else CPU). m1 embeds passages
    with **no prefix** and loads the plain BERT arch with **no**
    ``trust_remote_code`` (see ``creative-embedding-model-selection.md``).
    """

    def __init__(self, model_name: str = EMBED_MODEL) -> None:
        silence_unauthenticated_hub_warning()
        import torch  # noqa: PLC0415 — lazy: keep torch off the module import path
        from sentence_transformers import SentenceTransformer  # noqa: PLC0415

        device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = SentenceTransformer(
            model_name, device=device, trust_remote_code=False
        )

    def encode(self, texts: list[str]) -> list[list[float]]:
        """Encode ``texts`` into 384-dim vectors (no passage prefix for m1)."""
        vectors = self.model.encode(texts, convert_to_numpy=True)
        return [vector.tolist() for vector in vectors]


def _missing_torch(exc: BaseException) -> bool:
    """True when ``exc`` is a failed import of ``torch`` or ``torch.*``."""
    if not isinstance(exc, ModuleNotFoundError):
        return False
    name = exc.name or ""
    return name == "torch" or name.startswith("torch.")


def missing_torch_remedy() -> str:
    """Return the report-only remedy when ``import torch`` fails.

    A usable hashed freeze names ``stockroom shim ensure-env``. Otherwise
    the clause is ``sr-initialize``. This is what ``doctor smoke`` prints.
    ``semantic`` and ``embed`` restore from the freeze themselves.
    """
    if read_freeze_path() is not None:
        return (
            "restore it with `stockroom shim ensure-env` "
            "(or re-run sr-initialize to re-pick a wheel)"
        )
    return "re-run sr-initialize (install → smoke → freeze)"


def encoder_load_remedy() -> str:
    """Return the remedy clause when the encoder fails after torch imports.

    The clause names ``sr-initialize``. It does not claim the wheel is wrong:
    the exception may be a download failure or a bug, not a bad build.
    """
    return "re-run sr-initialize"


def _encoder_failed_line(exc: BaseException) -> str:
    """One stderr line for a construction failure that is not a torch restore."""
    return (
        f"error: encoder check failed ({exc.__class__.__name__}: {exc}) — "
        f"{encoder_load_remedy()}"
    )


def _torch_missing_line(app_dir: Path) -> str:
    """One stderr line when torch is missing and there is nothing to restore."""
    diagnosis = f"torch is not installed in the engine environment at {app_dir}"
    return f"error: {diagnosis} — {missing_torch_remedy()}"


def start_encoder(
    factory: Callable[[], Encoder],
    *,
    healer: Callable[[Path], EnsureReport] | None = None,
) -> Encoder | None:
    """Build ``factory``, restoring torch once when a usable freeze can.

    A missing ``torch`` import with a usable hashed freeze prints
    ``restoring torch from the hashed freeze``, calls ``healer`` (default
    :func:`stockroom.engine_env.ensure_engine_env`) once, and retries
    ``factory`` once when the report is not ``failed``. Any other failure
    prints one stderr line and returns ``None``. A non-torch
    ``ModuleNotFoundError`` propagates.
    """
    try:
        return factory()
    except ModuleNotFoundError as exc:
        if not _missing_torch(exc):
            raise
        app_dir = default_app_dir()
        if read_freeze_path() is None:
            print(_torch_missing_line(app_dir), file=sys.stderr)
            return None
        print("restoring torch from the hashed freeze", file=sys.stderr)
        restore = (healer or ensure_engine_env)(app_dir)
        if restore.action == "failed":
            print(
                f"error: torch restore failed ({restore.reason}) — "
                "re-run sr-initialize",
                file=sys.stderr,
            )
            return None
        importlib.invalidate_caches()
        try:
            return factory()
        except ModuleNotFoundError as retry_exc:
            if not _missing_torch(retry_exc):
                raise
            print(_encoder_failed_line(retry_exc), file=sys.stderr)
            return None
        except Exception as retry_exc:
            print(_encoder_failed_line(retry_exc), file=sys.stderr)
            return None
    except Exception as exc:
        print(_encoder_failed_line(exc), file=sys.stderr)
        return None


def _build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for ``python -m stockroom.embed``."""
    parser = argparse.ArgumentParser(
        prog="python -m stockroom.embed",
        description=(
            "Embed warehouse message text into the embeddings table "
            "(incremental by default)."
        ),
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Re-embed all messages, ignoring existing rows (mirrors ingest --full).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print progress while embedding (quiet by default).",
    )
    return parser


def main(
    argv: list[str] | None = None,
    *,
    encoder_factory: Callable[[], Encoder] = BgeEncoder,
    healer: Callable[[Path], EnsureReport] | None = None,
) -> int:
    """Parse args, embed pending message text read-write, print the count.

    Returns ``0`` on success, ``1`` when no warehouse exists yet (with a clean
    "run ingest first" hint and no traceback — checked *before* the encoder is
    built, so the friendly path needs no torch) or when the encoder cannot be
    constructed. A missing torch with a usable freeze is restored once and the
    embed retried. Any other construction failure prints one stderr line
    naming ``sr-initialize``. Opens the warehouse read-write through
    ``warehouse.open()`` (so ``vss`` is loaded and the schema is current) and
    constructs the encoder via ``encoder_factory`` (default :class:`BgeEncoder`,
    which loads torch out of band; tests inject a fake).
    """
    args = _build_parser().parse_args(argv)

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
    on_progress = (lambda line: print(line, flush=True)) if args.verbose else None
    con = warehouse.open(read_only=False)
    try:
        written = embed_pending(con, encoder, full=args.full, on_progress=on_progress)
    finally:
        con.close()

    print(f"embedded {written} chunk vector{'' if written == 1 else 's'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
