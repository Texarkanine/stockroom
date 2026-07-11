"""End-to-end tests for ``python -m stockroom.query``.

These run the entrypoint as a real subprocess against a throwaway
``STOCKROOM_HOME``. The happy-path / proof tests first populate that warehouse
by running the milestone-3 ``python -m stockroom.ingest`` against the env-pointed
fixture roots — exercising the full ingest→query loop (ingest → query) the way a real
user would, and proving the database is genuinely queryable end to end.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import stockroom

_SRC_DIR = str(Path(stockroom.__file__).parent.parent)


def _base_env(home: Path) -> dict:
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([_SRC_DIR, env.get("PYTHONPATH", "")]).rstrip(
        os.pathsep
    )
    env["STOCKROOM_HOME"] = str(home)
    return env


def _ingest(
    home: Path, cursor_root: Path, claude_root: Path, ai_tracking_db: Path
) -> None:
    """Populate ``home``'s warehouse via a real ``--full`` ingest subprocess."""
    env = _base_env(home)
    env["STOCKROOM_CURSOR_ROOT"] = str(cursor_root)
    env["STOCKROOM_CLAUDE_ROOT"] = str(claude_root)
    env["STOCKROOM_AI_TRACKING_DB"] = str(ai_tracking_db)
    result = subprocess.run(
        [sys.executable, "-m", "stockroom.ingest", "--full"],
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def _run_query(
    *args: str, home: Path, stdin: str | None = None
) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "stockroom.query", *args],
        env=_base_env(home),
        input=stdin,
        capture_output=True,
        text=True,
    )


def test_query_happy_path_prints_result(
    tmp_path: Path, cursor_root: Path, claude_root: Path, ai_tracking_db: Path
) -> None:
    """``SELECT 1 AS n`` against an ingested warehouse exits 0 and prints the
    column and value."""
    home = tmp_path / "home"
    _ingest(home, cursor_root, claude_root, ai_tracking_db)

    result = _run_query("SELECT 1 AS n", home=home)
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == ["n", "1"]


def test_query_after_ingest_returns_distinct_harnesses(
    tmp_path: Path, cursor_root: Path, claude_root: Path, ai_tracking_db: Path
) -> None:
    """A DISTINCT-harness query over a
    freshly-ingested warehouse names both ``cursor`` and ``claude``."""
    home = tmp_path / "home"
    _ingest(home, cursor_root, claude_root, ai_tracking_db)

    result = _run_query(
        "SELECT DISTINCT harness FROM sessions ORDER BY harness", home=home
    )
    assert result.returncode == 0, result.stderr
    assert "cursor" in result.stdout
    assert "claude" in result.stdout


def test_query_invalid_sql_is_clean_error(
    tmp_path: Path, cursor_root: Path, claude_root: Path, ai_tracking_db: Path
) -> None:
    """Invalid SQL exits nonzero with a stderr message and no Python traceback."""
    home = tmp_path / "home"
    _ingest(home, cursor_root, claude_root, ai_tracking_db)

    result = _run_query("SELEKT 1", home=home)
    assert result.returncode != 0
    assert result.stderr.strip() != ""
    assert "Traceback" not in result.stderr


def test_query_read_only_rejects_writes(
    tmp_path: Path, cursor_root: Path, claude_root: Path, ai_tracking_db: Path
) -> None:
    """A write statement is rejected (read-only surface) and exits nonzero."""
    home = tmp_path / "home"
    _ingest(home, cursor_root, claude_root, ai_tracking_db)

    result = _run_query("CREATE TABLE scratch (x INTEGER)", home=home)
    assert result.returncode != 0
    assert "Traceback" not in result.stderr
    # The write never landed: querying the would-be table fails too.
    check = _run_query("SELECT * FROM scratch", home=home)
    assert check.returncode != 0


def test_query_missing_warehouse_is_friendly(tmp_path: Path) -> None:
    """Querying with no warehouse present exits nonzero with a 'run ingest'
    hint rather than a raw IOException/traceback. The hint names the on-path
    command (`stockroom ingest`), never a raw module invocation — pinned
    exactly so the message cannot drift back."""
    home = tmp_path / "empty-home"
    result = _run_query("SELECT 1", home=home)
    assert result.returncode != 0
    assert "Traceback" not in result.stderr
    assert "run `stockroom ingest` first" in result.stderr


def test_query_empty_sql_is_rejected(tmp_path: Path) -> None:
    """An empty / whitespace-only query exits nonzero with a message and never
    opens the warehouse."""
    home = tmp_path / "home"
    result = _run_query("   ", home=home)
    assert result.returncode != 0
    assert result.stderr.strip() != ""


def test_query_detail_controls_truncation(
    tmp_path: Path, cursor_root: Path, claude_root: Path, ai_tracking_db: Path
) -> None:
    """The default elides a wide cell with a marker; ``--detail full`` prints it
    whole; ``--detail compact`` is terser than the default."""
    home = tmp_path / "home"
    _ingest(home, cursor_root, claude_root, ai_tracking_db)
    sql = "SELECT repeat('x', 500) AS big"

    default = _run_query(sql, home=home)
    assert default.returncode == 0, default.stderr
    assert "x" * 500 not in default.stdout
    assert "…" in default.stdout

    full = _run_query("--detail", "full", sql, home=home)
    assert full.returncode == 0, full.stderr
    assert "x" * 500 in full.stdout

    compact = _run_query("--detail", "compact", sql, home=home)
    assert compact.returncode == 0, compact.stderr
    # The terser level keeps fewer 'x' content characters before its marker.
    assert compact.stdout.count("x") < default.stdout.count("x")


def test_query_invalid_detail_is_rejected(tmp_path: Path) -> None:
    """An unknown ``--detail`` value is rejected by argparse (exit 2) before any
    warehouse access."""
    result = _run_query("--detail", "bogus", "SELECT 1", home=tmp_path / "home")
    assert result.returncode == 2
    assert result.stderr.strip() != ""


def test_query_detail_raw_is_accepted(
    tmp_path: Path, cursor_root: Path, claude_root: Path, ai_tracking_db: Path
) -> None:
    """``--detail raw`` is a valid argparse choice and preserves newlines in json."""
    home = tmp_path / "home"
    _ingest(home, cursor_root, claude_root, ai_tracking_db)
    sql = "SELECT 'a' || chr(10) || 'b' AS t"
    result = _run_query("--format", "json", "--detail", "raw", sql, home=home)
    assert result.returncode == 0, result.stderr
    parsed = json.loads(result.stdout)
    assert parsed["rows"][0][0] == "a\nb"


def test_query_reads_sql_from_stdin(
    tmp_path: Path, cursor_root: Path, claude_root: Path, ai_tracking_db: Path
) -> None:
    """The ``-`` sentinel reads the statement from stdin."""
    home = tmp_path / "home"
    _ingest(home, cursor_root, claude_root, ai_tracking_db)

    result = _run_query("-", home=home, stdin="SELECT 1 AS n")
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == ["n", "1"]


def test_query_default_output_is_tsv(
    tmp_path: Path, cursor_root: Path, claude_root: Path, ai_tracking_db: Path
) -> None:
    """With no ``--format`` the output is tsv: a tab-separated header + data line,
    no ``" | "`` table art and no ``(N rows)`` trailer."""
    home = tmp_path / "home"
    _ingest(home, cursor_root, claude_root, ai_tracking_db)

    result = _run_query("SELECT 1 AS a, 2 AS b", home=home)
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == ["a\tb", "1\t2"]
    assert " | " not in result.stdout
    assert "(1 row)" not in result.stdout


def test_query_format_table_restores_table(
    tmp_path: Path, cursor_root: Path, claude_root: Path, ai_tracking_db: Path
) -> None:
    """``--format table`` restores the column-aligned table and its trailer."""
    home = tmp_path / "home"
    _ingest(home, cursor_root, claude_root, ai_tracking_db)

    result = _run_query("--format", "table", "SELECT 1 AS a, 2 AS b", home=home)
    assert result.returncode == 0, result.stderr
    assert " | " in result.stdout
    assert result.stdout.rstrip().endswith("(1 row)")


def test_query_format_json_parses(
    tmp_path: Path, cursor_root: Path, claude_root: Path, ai_tracking_db: Path
) -> None:
    """``--format json`` emits a single parseable ``{"columns", "rows"}`` object."""
    home = tmp_path / "home"
    _ingest(home, cursor_root, claude_root, ai_tracking_db)

    result = _run_query("--format", "json", "SELECT 1 AS a, 2 AS b", home=home)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"columns": ["a", "b"], "rows": [["1", "2"]]}


def test_query_invalid_format_is_rejected(tmp_path: Path) -> None:
    """An unknown ``--format`` value is rejected by argparse (exit 2) before any
    warehouse access."""
    result = _run_query("--format", "bogus", "SELECT 1", home=tmp_path / "home")
    assert result.returncode == 2
    assert result.stderr.strip() != ""
