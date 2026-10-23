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


def test_migrate_below_schema_three_prints_one_line_and_a_working_mv(
    tmp_path: Path,
) -> None:
    """W5: a schema-1 warehouse fails with one stderr line and a usable remedy.

    The home path holds a space and a ``'``. ``stockroom migrate`` exits 1
    with a single ``migrate failed:`` line that names the file, and no
    traceback. The ``mv`` command in that line, run through ``sh -c``, moves
    the file aside.
    """
    import re

    import duckdb

    from stockroom import migrate
    from stockroom.migrations import discover

    home = tmp_path / "it's a home"
    home.mkdir()
    db = home / "warehouse.duckdb"
    con = duckdb.connect(str(db), config={"storage_compatibility_version": "v1.0.0"})
    try:
        first = discover()[0]
        migrate.ensure_schema_version_table(con)
        con.execute(first.path.read_text(encoding="utf-8"))
        con.execute(
            f"INSERT INTO {migrate.SCHEMA_VERSION_TABLE} (version, filename) "
            "VALUES (?, ?)",
            [first.version, first.path.name],
        )
    finally:
        con.close()

    result = _run_migrate(home=home)

    assert result.returncode == 1
    assert result.stdout == ""
    lines = result.stderr.splitlines()
    assert len(lines) == 1, result.stderr
    assert lines[0].startswith("migrate failed: ")
    assert str(db) in lines[0]
    assert "Traceback" not in result.stderr
    command = re.search(r"for example: (mv .+), then run", lines[0])
    assert command is not None, lines[0]

    moved = subprocess.run(["sh", "-c", command.group(1)], capture_output=True)

    assert moved.returncode == 0, moved.stderr
    assert not db.exists()
    assert (home / "warehouse.duckdb.old").is_file()
