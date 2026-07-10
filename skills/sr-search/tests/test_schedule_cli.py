"""End-to-end tests for the ``stockroom.schedule`` CLI (subprocess convention).

Runs ``python -m stockroom.schedule`` as a real subprocess (the
``test_doctor_cli.py`` convention), exercising real argv parsing and the
action dispatch (B15). The environment is fully injected through the
process seams: ``STOCKROOM_HOME`` redirects the log-path facts away from
the operator's real home, and a stub ``crontab`` executable prepended to
``PATH`` stands in for the real user crontab (reporting "no crontab" so
the status is deterministically "not installed"). These tests assume the
CI/dev platform is Linux (the cron path) — the platform seam itself is
unit-tested in ``test_schedule.py``.
"""

import os
import platform
import subprocess
import sys
from pathlib import Path

import pytest

import stockroom

_SRC_DIR = str(Path(stockroom.__file__).parent.parent)


@pytest.fixture
def stub_crontab(tmp_path: Path) -> Path:
    """Write a stub ``crontab`` executable and return its bin dir.

    ``-l`` exits 1 with "no crontab" (the empty-crontab shape); any write
    attempt fails loudly so a test can never touch a real crontab even if
    the stub leaks into an install path.
    """
    bin_dir = tmp_path / "stub-bin"
    bin_dir.mkdir(exist_ok=True)
    crontab = bin_dir / "crontab"
    crontab.write_text(
        "#!/bin/sh\n"
        'if [ "$1" = -l ]; then\n'
        "    echo 'no crontab for user' >&2\n"
        "    exit 1\n"
        "fi\n"
        "echo 'stub crontab: unexpected write' >&2\n"
        "exit 99\n",
        encoding="utf-8",
    )
    crontab.chmod(0o755)
    return bin_dir


def _run(
    *args: str, home: Path, extra_path: Path | None = None
) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([_SRC_DIR, env.get("PYTHONPATH", "")]).rstrip(
        os.pathsep
    )
    env["STOCKROOM_HOME"] = str(home)
    if extra_path is not None:
        env["PATH"] = os.pathsep.join([str(extra_path), env.get("PATH", "")])
    return subprocess.run(
        [sys.executable, "-m", "stockroom.schedule", *args],
        env=env,
        capture_output=True,
        text=True,
    )


def test_help_documents_actions_and_time_flag(tmp_path: Path) -> None:
    """B15: ``--help`` exits 0 and documents install, status, remove, and
    the ``--time`` flag with its default."""
    result = _run("--help", home=tmp_path / "home")
    assert result.returncode == 0, result.stderr
    for token in ("install", "status", "remove", "--time", "03:30"):
        assert token in result.stdout, f"help missing {token!r}: {result.stdout}"


def test_invalid_action_is_clean_error(tmp_path: Path) -> None:
    """B15: an invalid action exits 2 with argparse's clean error (no
    traceback)."""
    result = _run("bogus", home=tmp_path / "home")
    assert result.returncode == 2
    assert "Traceback" not in result.stderr


def test_status_against_empty_environment(tmp_path: Path, stub_crontab: Path) -> None:
    """B15: ``status`` through real argv parsing against an injected-empty
    environment (stubbed crontab, redirected home) exits 0 and reports the
    not-installed, daemon, and log facts."""
    if platform.system() != "Linux":
        pytest.skip("cron-path CLI test — Linux only (launchd is unit-tested)")
    home = tmp_path / "home"
    result = _run("status", home=home, extra_path=stub_crontab)
    assert result.returncode == 0, result.stderr
    assert "not installed" in result.stdout
    assert "daemon:" in result.stdout
    assert f"log: {home / 'logs' / 'nightly.log'}" in result.stdout
