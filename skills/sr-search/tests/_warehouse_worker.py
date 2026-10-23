"""Subprocess worker for the warehouse concurrency and old-warehouse tests.

Not a test module (the leading underscore keeps pytest from collecting it).
It is launched via ``sys.executable`` by the ``spawn_worker`` fixture with the
engine ``src`` on ``PYTHONPATH`` and ``STOCKROOM_HOME`` pointing at the test's
temporary warehouse home, so a child runs in a genuinely separate process and
exercises DuckDB's *cross-process* file lock (a second connection in the same
process would merely share the instance). The old-warehouse commands load
``vss`` here, in the child, so the test process itself never loads it.

Commands:

* ``hold_rw <ready_file> <seconds>`` — open the warehouse read-write directly
  (simulating an in-progress migration holding the exclusive lock), signal
  readiness, hold for ``seconds``, then release.
* ``hold_ro <ready_file> <seconds>`` — same, but a shared read-only hold.
* ``migrate_report <out_file>`` — open the warehouse as a writer through the
  real chokepoint (lazy gate + flock), then write the observed schema version
  to ``out_file``. Used to race two would-be migrators.
* ``build_indexed <db> <rows> <scratch_dir>`` — build the warehouse a v2.1.2
  install left: a ``v1.0.0`` file at schema 8 with the HNSW index, ``<rows>``
  messages, and one one-hot embedding per message at slots ``0..rows-1``.
  Checkpoints, closes, and prints ``built``.
* ``build_chain <db> <through> <rows> <storage> <scratch_dir>`` — build the
  packaged chain through version ``<through>`` into a new file at storage
  version ``<storage>``, with ``vss`` loaded when ``<through>`` is 3 or more,
  then write ``<rows>`` messages with one one-hot embedding each, as
  ``build_indexed`` does. Checkpoints, closes, and prints ``built``.
* ``index_knn_delete <db> <out_file>`` — with ``vss`` loaded, insert three
  one-hot embeddings ``s#0`` to ``s#2`` into a file that has the ``0003``
  index, find the nearest to ``s#0``'s vector, delete ``s#0``, and write
  ``{"nearest": …, "count": …}`` to ``out_file`` as JSON.
* ``insert_and_hang <db> <ready_file>`` — with ``vss`` loaded, insert message
  ``k#0`` and its embedding (one-hot at slot 300), commit, signal readiness,
  then sleep until killed: an embed killed with the index up.
* ``migrate_and_hang <ready_file>`` — open the warehouse as a writer through
  the real chokepoint (which migrates), signal readiness, then sleep until
  killed: a migrator killed before it closes.
"""

import json
import shutil
import sys
import time
from pathlib import Path

import duckdb

from stockroom import warehouse
from stockroom.migrate import apply_pending, current_version
from stockroom.migrations import discover

#: Migration ``0003`` as v2.1.2 shipped it, as ``0003_embeddings_hnsw_index.sql``.
#: It needs ``vss`` loaded. The packaged ``0003`` is retired.
V2_1_2_INDEX_SQL = (
    "SET hnsw_enable_experimental_persistence = true;\n"
    "CREATE INDEX embeddings_vector_hnsw ON embeddings USING HNSW (vector) "
    "WITH (metric = 'cosine');\n"
)

#: Slot of the one-hot vector ``insert_and_hang`` writes.
KILLED_SLOT = 300


def one_hot(slot: int) -> list[float]:
    """A 384-vector with 1.0 at ``slot``: one distinct cosine direction per slot."""
    vector = [0.0] * 384
    vector[slot] = 1.0
    return vector


def _load_vss(con: duckdb.DuckDBPyConnection) -> None:
    """Load ``vss`` (installing it once if needed) and allow writes to its index."""
    try:
        con.execute("LOAD vss")
    except duckdb.Error:
        con.execute("INSTALL vss")
        con.execute("LOAD vss")
    con.execute("SET hnsw_enable_experimental_persistence = true")


def build_v2_1_2_chain(con: duckdb.DuckDBPyConnection, directory: Path) -> None:
    """Apply the migration chain v2.1.2 shipped (versions 1 to 8) to ``con``.

    Writes the packaged ``0001``, ``0002``, and ``0004`` to ``0008`` into
    ``directory`` under their own names, writes :data:`V2_1_2_INDEX_SQL` as
    ``0003_embeddings_hnsw_index.sql``, and runs the real runner on that
    directory. ``vss`` must already be loaded on ``con``.
    """
    directory.mkdir(parents=True, exist_ok=True)
    for migration in discover():
        if migration.version == 3 or migration.version > 8:
            continue
        (directory / migration.path.name).write_text(
            migration.path.read_text(encoding="utf-8"), encoding="utf-8"
        )
    (directory / "0003_embeddings_hnsw_index.sql").write_text(
        V2_1_2_INDEX_SQL, encoding="utf-8"
    )
    apply_pending(con, directory)


def build_released_chain(
    con: duckdb.DuckDBPyConnection, through: int, directory: Path
) -> list[int]:
    """Apply the packaged migrations up to ``through`` to ``con``; return them.

    Copies each packaged migration whose version is ``through`` or lower into
    ``directory`` under its own name and runs the real runner there. When the
    chain reaches ``0003``, ``vss`` must already be loaded on ``con``.
    """
    directory.mkdir(parents=True, exist_ok=True)
    for migration in discover():
        if migration.version <= through:
            shutil.copyfile(migration.path, directory / migration.path.name)
    return apply_pending(con, directory)


def _insert_message(
    con: duckdb.DuckDBPyConnection, message_id: str, ordinal: int, slot: int
) -> None:
    session_id = message_id.split("#", 1)[0]
    con.execute(
        "INSERT INTO messages (harness, session_id, message_id, ordinal, role, text) "
        "VALUES ('claude', ?, ?, ?, 'user', ?)",
        [session_id, message_id, ordinal, f"message {message_id}"],
    )
    con.execute(
        "INSERT INTO embeddings "
        "(harness, owner_table, owner_id, chunk_index, embed_model, vector) "
        "VALUES ('claude', 'messages', ?, 0, 'fake', ?)",
        [message_id, one_hot(slot)],
    )


def _build_indexed(db: str, rows: str, scratch_dir: str) -> None:
    con = duckdb.connect(db, config={"storage_compatibility_version": "v1.0.0"})
    try:
        _load_vss(con)
        build_v2_1_2_chain(con, Path(scratch_dir))
        for ordinal in range(int(rows)):
            _insert_message(con, f"b#{ordinal}", ordinal, ordinal)
        con.execute("CHECKPOINT")
    finally:
        con.close()
    print("built", flush=True)


def _build_chain(
    db: str, through: str, rows: str, storage: str, scratch_dir: str
) -> None:
    con = duckdb.connect(db, config={"storage_compatibility_version": storage})
    try:
        if int(through) >= 3:
            _load_vss(con)
        build_released_chain(con, int(through), Path(scratch_dir))
        for ordinal in range(int(rows)):
            _insert_message(con, f"b#{ordinal}", ordinal, ordinal)
        con.execute("CHECKPOINT")
    finally:
        con.close()
    print("built", flush=True)


def _index_knn_delete(db: str, out_file: str) -> None:
    con = duckdb.connect(db)
    try:
        _load_vss(con)
        for ordinal in range(3):
            con.execute(
                "INSERT INTO embeddings "
                "(harness, owner_table, owner_id, chunk_index, embed_model, vector) "
                "VALUES ('claude', 'messages', ?, 0, 'm', ?)",
                [f"s#{ordinal}", one_hot(ordinal)],
            )
        nearest = con.execute(
            "SELECT owner_id FROM embeddings "
            "ORDER BY array_cosine_distance(vector, ?::FLOAT[384]) LIMIT 1",
            [one_hot(0)],
        ).fetchone()[0]
        con.execute("DELETE FROM embeddings WHERE owner_id = 's#0'")
        count = con.execute("SELECT count(*) FROM embeddings").fetchone()[0]
    finally:
        con.close()
    Path(out_file).write_text(
        json.dumps({"nearest": nearest, "count": count}), encoding="utf-8"
    )


def _insert_and_hang(db: str, ready_file: str) -> None:
    con = duckdb.connect(db)
    _load_vss(con)
    _insert_message(con, "k#0", 0, KILLED_SLOT)
    Path(ready_file).write_text("ready", encoding="utf-8")
    time.sleep(3600)


def _migrate_and_hang(ready_file: str) -> None:
    con = warehouse.open(read_only=False)
    Path(ready_file).write_text(str(current_version(con)), encoding="utf-8")
    time.sleep(3600)


def _hold(ready_file: str, seconds: str, *, read_only: bool) -> None:
    con = duckdb.connect(str(warehouse.warehouse_path()), read_only=read_only)
    try:
        Path(ready_file).write_text("ready", encoding="utf-8")
        time.sleep(float(seconds))
    finally:
        con.close()


def _migrate_report(out_file: str) -> None:
    con = warehouse.open(read_only=False)
    try:
        Path(out_file).write_text(str(current_version(con)), encoding="utf-8")
    finally:
        con.close()


def main(argv: list[str]) -> None:
    command, *rest = argv
    if command == "hold_rw":
        _hold(rest[0], rest[1], read_only=False)
    elif command == "hold_ro":
        _hold(rest[0], rest[1], read_only=True)
    elif command == "migrate_report":
        _migrate_report(rest[0])
    elif command == "build_indexed":
        _build_indexed(rest[0], rest[1], rest[2])
    elif command == "build_chain":
        _build_chain(rest[0], rest[1], rest[2], rest[3], rest[4])
    elif command == "index_knn_delete":
        _index_knn_delete(rest[0], rest[1])
    elif command == "insert_and_hang":
        _insert_and_hang(rest[0], rest[1])
    elif command == "migrate_and_hang":
        _migrate_and_hang(rest[0])
    else:  # pragma: no cover - defensive
        raise SystemExit(f"unknown worker command: {command}")


if __name__ == "__main__":
    main(sys.argv[1:])
