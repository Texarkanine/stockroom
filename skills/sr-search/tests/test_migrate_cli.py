"""End-to-end tests for ``python -m stockroom.migrate``.

These run the new migrate CLI as a real subprocess against a throwaway
``STOCKROOM_HOME`` (the ``test_query_cli.py`` convention). The CLI wraps the
``warehouse.open()`` chokepoint, whose lazy gate creates a missing warehouse
and migrates it to the schema head — so an explicit migrate is the schema
bootstrap command, and re-running it is an idempotent version report.
"""

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


def _run_migrate(*args: str, home: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "stockroom.migrate", *args],
        env=_base_env(home),
        capture_output=True,
        text=True,
    )


def test_migrate_fresh_home_bootstraps_warehouse(tmp_path: Path) -> None:
    """Against an empty STOCKROOM_HOME, migrate exits 0, creates the warehouse
    file, and reports the head schema version on stdout."""
    from stockroom.migrations import discover

    home = tmp_path / "home"
    result = _run_migrate(home=home)
    assert result.returncode == 0, result.stderr
    assert (home / "warehouse.duckdb").is_file()
    head = discover()[-1].version
    assert str(head) in result.stdout


def test_migrate_is_idempotent(tmp_path: Path) -> None:
    """A second run against the same home exits 0 and reports the same
    version with no error output."""
    home = tmp_path / "home"
    first = _run_migrate(home=home)
    assert first.returncode == 0, first.stderr

    second = _run_migrate(home=home)
    assert second.returncode == 0, second.stderr
    assert second.stdout == first.stdout
    assert second.stderr.strip() == ""


def test_migrate_help_mentions_migration(tmp_path: Path) -> None:
    """``--help`` exits 0 and the description mentions migration."""
    result = _run_migrate("--help", home=tmp_path / "home")
    assert result.returncode == 0
    assert "migrat" in result.stdout.lower()
