"""CLI smoke tests for ``python -m stockroom.ingest``.

These run the entrypoint as a real subprocess against the env-pointed fixture
roots and a throwaway ``STOCKROOM_HOME`` warehouse, exercising the full
con=None path (open the warehouse RW through the milestone-2 chokepoint, ingest,
print a summary, exit 0) end to end — the closest thing to a live ingest the
suite has.
"""

import os
import subprocess
import sys
from pathlib import Path

import duckdb

import stockroom

_SRC_DIR = str(Path(stockroom.__file__).parent.parent)


def _run_cli(
    *args: str,
    home: Path,
    cursor_root: Path,
    claude_root: Path,
    ai_tracking_db: Path,
) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([_SRC_DIR, env.get("PYTHONPATH", "")]).rstrip(
        os.pathsep
    )
    env["STOCKROOM_HOME"] = str(home)
    env["STOCKROOM_CURSOR_ROOT"] = str(cursor_root)
    env["STOCKROOM_CLAUDE_ROOT"] = str(claude_root)
    env["STOCKROOM_AI_TRACKING_DB"] = str(ai_tracking_db)
    return subprocess.run(
        [sys.executable, "-m", "stockroom.ingest", *args],
        env=env,
        capture_output=True,
        text=True,
    )


def _warehouse_harnesses(home: Path) -> set[str]:
    con = duckdb.connect(str(home / "warehouse.duckdb"), read_only=True)
    try:
        return {
            r[0]
            for r in con.execute("SELECT DISTINCT harness FROM sessions").fetchall()
        }
    finally:
        con.close()


def test_cli_full_single_harness_writes_only_that_harness(
    tmp_path: Path,
    cursor_root: Path,
    claude_root: Path,
    ai_tracking_db: Path,
) -> None:
    """``--full --harness claude`` exits 0 and writes only Claude rows."""
    home = tmp_path / "home"
    result = _run_cli(
        "--full",
        "--harness",
        "claude",
        home=home,
        cursor_root=cursor_root,
        claude_root=claude_root,
        ai_tracking_db=ai_tracking_db,
    )
    assert result.returncode == 0, result.stderr
    assert _warehouse_harnesses(home) == {"claude"}


def test_cli_full_both_harnesses_and_summary(
    tmp_path: Path,
    cursor_root: Path,
    claude_root: Path,
    ai_tracking_db: Path,
) -> None:
    """A default ``--full`` run ingests both harnesses and prints a summary."""
    home = tmp_path / "home"
    result = _run_cli(
        "--full",
        home=home,
        cursor_root=cursor_root,
        claude_root=claude_root,
        ai_tracking_db=ai_tracking_db,
    )
    assert result.returncode == 0, result.stderr
    assert _warehouse_harnesses(home) == {"cursor", "claude"}
    # The summary names both harnesses.
    assert "cursor" in result.stdout
    assert "claude" in result.stdout


def test_cli_rejects_unknown_harness(
    tmp_path: Path,
    cursor_root: Path,
    claude_root: Path,
    ai_tracking_db: Path,
) -> None:
    """An unknown ``--harness`` value is rejected by argparse (nonzero exit)."""
    home = tmp_path / "home"
    result = _run_cli(
        "--harness",
        "aider",
        home=home,
        cursor_root=cursor_root,
        claude_root=claude_root,
        ai_tracking_db=ai_tracking_db,
    )
    assert result.returncode != 0


def test_cli_quiet_default_has_no_mid_run_progress(
    tmp_path: Path,
    cursor_root: Path,
    claude_root: Path,
    ai_tracking_db: Path,
) -> None:
    """Without ``--verbose``, stdout is only the end-of-run summary."""
    home = tmp_path / "home"
    result = _run_cli(
        "--full",
        "--harness",
        "claude",
        home=home,
        cursor_root=cursor_root,
        claude_root=claude_root,
        ai_tracking_db=ai_tracking_db,
    )
    assert result.returncode == 0, result.stderr
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    assert lines[0] == "ingest complete:"
    assert any("claude:" in line for line in lines)
    assert not any("/" in line and "sessions" in line for line in lines)


def test_cli_verbose_prints_progress_and_summary(
    tmp_path: Path,
    cursor_root: Path,
    claude_root: Path,
    ai_tracking_db: Path,
) -> None:
    """``--verbose`` emits harness progress lines and still prints the summary."""
    home = tmp_path / "home"
    result = _run_cli(
        "--full",
        "--verbose",
        "--harness",
        "claude",
        home=home,
        cursor_root=cursor_root,
        claude_root=claude_root,
        ai_tracking_db=ai_tracking_db,
    )
    assert result.returncode == 0, result.stderr
    assert "claude: " in result.stdout
    assert any(
        "/" in line and line.strip().endswith("sessions")
        for line in result.stdout.splitlines()
    )
    assert "ingest complete:" in result.stdout
