"""End-to-end tests for ``stockroom backfill``.

These run the real command as a subprocess with ``STOCKROOM_HOME`` pointed at a
tmp dir (the ``test_query_cli.py`` convention), so they exercise argparse, the
warehouse chokepoint, and the exit-code contract together. Backfill reads an
operator's legacy store and writes to the shared warehouse, so its failure modes
matter as much as its success: an absent or unreadable store must produce one
line and a nonzero exit, never a traceback.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import duckdb
import pytest

import stockroom
from stockroom.backfill import cursor_vscdb

_SRC_DIR = str(Path(stockroom.__file__).parent.parent)


def _run(
    *args: str, home: Path, env_extra: dict | None = None
) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([_SRC_DIR, env.get("PYTHONPATH", "")]).rstrip(
        os.pathsep
    )
    env["STOCKROOM_HOME"] = str(home)
    env.pop(cursor_vscdb.STATE_VSCDB_ENV_VAR, None)
    # Isolate from the operator's real config.toml, which may pin a live store.
    env["XDG_CONFIG_HOME"] = str(home / "empty-config")
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, "-m", "stockroom", *args],
        env=env,
        capture_output=True,
        text=True,
    )


@pytest.fixture
def store(build_vscdb: Callable[..., Path]) -> Path:
    """A synthesized store holding one two-message composer with a tool call."""
    return build_vscdb(
        composers={
            "c1": {
                "name": "backfilled conversation",
                "fullConversationHeadersOnly": [
                    {"bubbleId": "b1", "type": 1},
                    {"bubbleId": "b2", "type": 2},
                ],
            }
        },
        bubbles={
            "c1:b1": {"type": 1, "text": "ask"},
            "c1:b2": {
                "type": 2,
                "text": "answer",
                "toolFormerData": {"name": "read_file", "rawArgs": json.dumps({})},
            },
        },
    )


def _session_count(home: Path) -> int:
    con = duckdb.connect(str(home / "warehouse.duckdb"), read_only=True)
    try:
        return con.execute("SELECT count(*) FROM sessions").fetchone()[0]
    finally:
        con.close()


def test_help_exits_zero_and_documents_the_flags(tmp_path: Path) -> None:
    """``--help`` names ``--dry-run`` and ``--source`` with the registered names."""
    result = _run("backfill", "--help", home=tmp_path / "home")
    assert result.returncode == 0, result.stderr
    assert "--dry-run" in result.stdout
    assert "--source" in result.stdout
    assert cursor_vscdb.NAME in result.stdout


def test_end_to_end_run_writes_rows_and_prints_a_summary(
    tmp_path: Path, store: Path
) -> None:
    """A real run against a synthesized store fills a real warehouse."""
    home = tmp_path / "home"
    result = _run("backfill", "--state-vscdb", str(store), home=home)
    assert result.returncode == 0, result.stderr
    assert cursor_vscdb.NAME in result.stdout
    assert _session_count(home) == 1


def test_dry_run_reports_without_writing(tmp_path: Path, store: Path) -> None:
    """``--dry-run`` prints the same counts but leaves the warehouse empty."""
    home = tmp_path / "home"
    result = _run("backfill", "--state-vscdb", str(store), "--dry-run", home=home)
    assert result.returncode == 0, result.stderr
    assert _session_count(home) == 0


def test_missing_store_exits_nonzero_with_one_line(tmp_path: Path) -> None:
    """An unconfigured store is a clean error, not a traceback."""
    result = _run("backfill", home=tmp_path / "home")
    assert result.returncode == 1
    assert "Traceback" not in result.stderr
    assert cursor_vscdb.STATE_VSCDB_ENV_VAR in result.stderr


def test_unreadable_store_exits_nonzero_with_one_line(tmp_path: Path) -> None:
    """A configured but unreadable store is a clean error, not a traceback."""
    absent = tmp_path / "nowhere" / "state.vscdb"
    result = _run("backfill", "--state-vscdb", str(absent), home=tmp_path / "home")
    assert result.returncode == 1
    assert "Traceback" not in result.stderr
    assert str(absent) in result.stderr


def test_unknown_source_exits_nonzero_listing_registered_sources(
    tmp_path: Path,
) -> None:
    """``--source bogus`` is rejected by argparse against the live registry."""
    result = _run("backfill", "--source", "bogus", home=tmp_path / "home")
    assert result.returncode != 0
    assert "Traceback" not in result.stderr
    assert cursor_vscdb.NAME in result.stderr


def test_verbose_emits_progress_lines(tmp_path: Path, store: Path) -> None:
    """``--verbose`` reports mid-run progress; the default stays quiet."""
    home = tmp_path / "home"
    verbose = _run("backfill", "--state-vscdb", str(store), "--verbose", home=home)
    assert verbose.returncode == 0, verbose.stderr

    quiet_home = tmp_path / "quiet-home"
    quiet = _run("backfill", "--state-vscdb", str(store), home=quiet_home)
    assert quiet.returncode == 0, quiet.stderr
    assert len(verbose.stdout.splitlines()) > len(quiet.stdout.splitlines())
