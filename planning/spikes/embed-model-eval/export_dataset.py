"""Export a known-item retrieval dataset from the warehouse to parquet.

Run with the sr-search project venv (has the migrated warehouse + duckdb 1.5.4):

    cd skills/sr-search && PYTHONPATH=src uv run --no-sync --no-config \
        python ../../planning/spikes/embed-model-eval/export_dataset.py

Produces two parquet files next to this script:

  * corpus.parquet  — the retrieval pool: every assistant message with
    >= 32 non-whitespace chars. uid = harness | '\\x1f' | message_id.
  * queries.parquet — labeled query->gold pairs: a user turn (the query) and
    the assistant turn that replied to it (the gold target, via parent_id),
    both >= 64 chars. gold_uid is guaranteed to be present in corpus.parquet.

The gold relevance signal is *structural*, not hand-labeled: within a session
an assistant message whose ``parent_id`` is a user message is, by construction,
the reply to that user turn. Across thousands of pairs this is a strong, honest
proxy for "does this model rank the right answer near the top" on Stockroom's
own data — no MTEB, no synthetic queries.
"""

from pathlib import Path

from stockroom import warehouse

OUT = Path(__file__).resolve().parent
SEP = "\x1f"  # unit separator — safe global uid delimiter

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
) TO '{OUT / "corpus.parquet"}' (FORMAT parquet);
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
) TO '{OUT / "queries.parquet"}' (FORMAT parquet);
"""


def main() -> int:
    con = warehouse.open(read_only=True)
    try:
        con.execute(CORPUS_SQL)
        con.execute(QUERIES_SQL)
        n_corpus = con.execute(
            f"SELECT count(*) FROM '{OUT / 'corpus.parquet'}'"
        ).fetchone()[0]
        n_queries = con.execute(
            f"SELECT count(*) FROM '{OUT / 'queries.parquet'}'"
        ).fetchone()[0]
        # Every gold must exist in the corpus pool, or the task is unscoreable.
        n_missing = con.execute(
            f"""
            SELECT count(*) FROM (
                SELECT DISTINCT gold_uid FROM '{OUT / 'queries.parquet'}'
            ) g
            WHERE g.gold_uid NOT IN (SELECT uid FROM '{OUT / 'corpus.parquet'}')
            """
        ).fetchone()[0]
    finally:
        con.close()

    print(f"corpus rows : {n_corpus}")
    print(f"query pairs : {n_queries}")
    print(f"gold not in corpus (must be 0): {n_missing}")
    return 0 if n_missing == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
