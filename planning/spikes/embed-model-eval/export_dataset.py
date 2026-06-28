"""Export a known-item retrieval dataset from the warehouse to parquet.

Portable: opens the DuckDB warehouse file **directly, read-only** — no
``stockroom``/``uv`` import — so it runs in the same plain interpreter as the
benchmark (handy on a second machine, e.g. a MacBook, with only
``pip install duckdb``). Warehouse path resolution mirrors
``stockroom.warehouse``:

    --db PATH                 explicit file
    $STOCKROOM_HOME/warehouse.duckdb
    ~/.stockroom/warehouse.duckdb   (default)

    python3 export_dataset.py [--db /path/to/warehouse.duckdb]

Produces two parquet files next to this script:

  * corpus.parquet  — the retrieval pool: every assistant message with
    >= 32 non-whitespace chars. uid = harness | '\\x1f' | message_id.
  * queries.parquet — labeled query->gold pairs: a user turn (the query) and
    the assistant turn that replied to it (the gold target, via parent_id),
    both >= 64 chars. gold_uid is guaranteed to be present in corpus.parquet.

The gold relevance signal is *structural*, not hand-labeled: within a session
an assistant message whose ``parent_id`` is a user message is, by construction,
the reply to that user turn. Across thousands of pairs this is a strong, honest
proxy for "does this model rank the right answer near the top" on this corpus —
no MTEB, no synthetic queries.

PRIVACY: the parquet files contain raw private message text and are gitignored.
Only ``results.json`` (metrics, no text) from ``benchmark.py`` is meant to leave
the machine.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import duckdb

HERE = Path(__file__).resolve().parent
SEP = "\x1f"  # unit separator — safe global uid delimiter


def resolve_warehouse(db_arg: str | None) -> Path:
    """Resolve the warehouse path: --db, else $STOCKROOM_HOME, else ~/.stockroom."""
    if db_arg:
        return Path(db_arg).expanduser()
    home = os.environ.get("STOCKROOM_HOME")
    base = Path(home).expanduser() if home else Path.home() / ".stockroom"
    return base / "warehouse.duckdb"


CORPUS_SQL = f"""
COPY (
    SELECT
        harness || '{SEP}' || message_id AS uid,
        harness,
        session_id,
        message_id,
        text
    FROM messages
    WHERE role = 'assistant'
      AND text IS NOT NULL
      AND length(trim(text)) >= 32
) TO '{{out}}' (FORMAT parquet);
"""

QUERIES_SQL = f"""
COPY (
    SELECT
        u.harness || '{SEP}' || u.message_id AS q_uid,
        u.text                                AS q_text,
        a.harness || '{SEP}' || a.message_id AS gold_uid
    FROM messages u
    JOIN messages a
      ON a.harness = u.harness
     AND a.session_id = u.session_id
     AND a.parent_id = u.message_id
    WHERE u.role = 'user'
      AND a.role = 'assistant'
      AND u.text IS NOT NULL
      AND a.text IS NOT NULL
      AND length(trim(u.text)) >= 64
      AND length(trim(a.text)) >= 64
) TO '{{out}}' (FORMAT parquet);
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=None, help="path to warehouse.duckdb")
    args = parser.parse_args()

    db = resolve_warehouse(args.db)
    if not db.is_file():
        print(f"error: no warehouse at {db} — set --db or $STOCKROOM_HOME, or run ingest first")
        return 1
    print(f"warehouse: {db}")

    corpus_pq = HERE / "corpus.parquet"
    queries_pq = HERE / "queries.parquet"

    con = duckdb.connect(str(db), read_only=True)
    try:
        con.execute(CORPUS_SQL.format(out=corpus_pq))
        con.execute(QUERIES_SQL.format(out=queries_pq))
        n_corpus = con.execute(f"SELECT count(*) FROM '{corpus_pq}'").fetchone()[0]
        n_queries = con.execute(f"SELECT count(*) FROM '{queries_pq}'").fetchone()[0]
        n_missing = con.execute(
            f"""
            SELECT count(*) FROM (
                SELECT DISTINCT gold_uid FROM '{queries_pq}'
            ) g
            WHERE g.gold_uid NOT IN (SELECT uid FROM '{corpus_pq}')
            """
        ).fetchone()[0]
    finally:
        con.close()

    print(f"corpus rows : {n_corpus}")
    print(f"query pairs : {n_queries}")
    print(f"gold not in corpus (must be 0): {n_missing}")
    if n_queries < 100:
        print("WARNING: very few query pairs — metrics will be noisy on this corpus.")
    return 0 if n_missing == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
