"""End-to-end tests for ``stockroom backfill``.

These run the real command as a subprocess with ``STOCKROOM_HOME`` pointed at a
tmp dir (the ``test_query_cli.py`` convention), so they exercise argparse, the
warehouse chokepoint, and the exit-code contract together. Backfill reads an
operator's legacy store and writes to the shared warehouse, so its failure modes
matter as much as its success: an absent or unreadable store must produce one
line and a nonzero exit, never a traceback.
"""

from __future__ import annotations

import fcntl
import json
import os
import subprocess
import sys
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path

import duckdb
import pytest

import stockroom
from stockroom import warehouse
from stockroom.backfill import cursor_vscdb

_SRC_DIR = str(Path(stockroom.__file__).parent.parent)


def _run(
    *args: str,
    home: Path,
    env_extra: dict | None = None,
    timeout: float | None = None,
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
        timeout=timeout,
    )


@contextmanager
def _held_writer_lock(home: Path) -> Iterator[None]:
    """Hold stockroom's single-writer flock for the body, as another process would."""
    fd = os.open(home / warehouse.LOCK_FILENAME, os.O_CREAT | os.O_RDWR, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
        fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


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


def test_help_states_the_required_operating_sequence(tmp_path: Path) -> None:
    """``--help`` names quit → ingest → backfill → embed.

    Both prerequisites fail silently when skipped — an unclean store read drops
    conversations without reporting them, and skipping ingest re-does embedding
    work — so the operator has to meet the order somewhere they will actually
    look, not only in the docs. Embed is step four because backfill never embeds.
    """
    result = _run("backfill", "--help", home=tmp_path / "home")
    assert result.returncode == 0, result.stderr
    out = result.stdout
    assert "do all four" in out
    assert "quit" in out.lower()
    assert "stockroom ingest" in out
    assert "stockroom backfill" in out
    assert "stockroom embed" in out
    assert out.index("stockroom ingest") < out.index("stockroom embed")


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
    assert _run("migrate", home=home).returncode == 0
    result = _run("backfill", "--state-vscdb", str(store), "--dry-run", home=home)
    assert result.returncode == 0, result.stderr
    assert _session_count(home) == 0


def test_dry_run_does_not_take_the_single_writer_lock(
    tmp_path: Path, store: Path
) -> None:
    """A dry run reads; only a real run queues behind the writer token.

    Both halves matter. Asserting only that the dry run succeeds would pass
    vacuously if the lock were never contended, so the same held lock is shown
    to block a real run.
    """
    home = tmp_path / "home"
    assert _run("migrate", home=home).returncode == 0

    with _held_writer_lock(home):
        dry = _run(
            "backfill", "--state-vscdb", str(store), "--dry-run", home=home, timeout=60
        )
        assert dry.returncode == 0, dry.stderr

        with pytest.raises(subprocess.TimeoutExpired):
            _run("backfill", "--state-vscdb", str(store), home=home, timeout=3)


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
