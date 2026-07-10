"""Unit tests for :mod:`stockroom.engine_env` (torch-safe ensure).

Uses an injectable ``runner`` so no real ``uv`` or network is required. The
contract under test is command shape + branching (noop / synced / failed),
not package installation.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from stockroom import engine_env


@pytest.fixture
def app_dir(tmp_path: Path) -> Path:
    """Engine dir with pyproject.toml (lock optional for unit branching)."""
    d = tmp_path / "engine"
    d.mkdir()
    (d / "pyproject.toml").write_text("[project]\nname = 'stockroom'\n")
    return d


def _ok(stdout: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=[], returncode=0, stdout=stdout, stderr=""
    )


def _fail(stderr: str = "outdated", code: int = 1) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=[], returncode=code, stdout="", stderr=stderr
    )


def test_noop_when_inexact_check_passes(app_dir: Path) -> None:
    """B1: usable env (check exit 0) → noop; heal sync never invoked."""
    calls: list[list[str]] = []

    def runner(cmd, **kwargs):  # noqa: ANN001
        calls.append(list(cmd))
        return _ok()

    report = engine_env.ensure_engine_env(app_dir, runner=runner)
    assert report.action == "noop"
    assert report.app_dir == Path(os.path.abspath(app_dir))
    assert len(calls) == 1
    assert calls[0][:4] == ["uv", "sync", "--frozen", "--inexact"]
    assert "--check" in calls[0]
    assert "--no-config" in calls[0]
    assert str(Path(os.path.abspath(app_dir))) in calls[0]


def test_heals_with_inexact_sync_when_check_fails(app_dir: Path) -> None:
    """B2: incomplete env → probe then heal; heal is frozen+inexact, no exact."""
    calls: list[list[str]] = []

    def runner(cmd, **kwargs):  # noqa: ANN001
        calls.append(list(cmd))
        if "--check" in cmd:
            return _fail()
        return _ok()

    report = engine_env.ensure_engine_env(app_dir, runner=runner)
    assert report.action == "synced"
    assert len(calls) == 2
    assert "--check" in calls[0]
    assert "--check" not in calls[1]
    for cmd in calls:
        assert "--inexact" in cmd
        assert "--frozen" in cmd
        # Never an exact sync: --inexact must always be present on heal path.
        assert cmd.count("--inexact") >= 1


def test_heal_command_never_omits_inexact(app_dir: Path) -> None:
    """B3: torch-safe — every uv sync argv from ensure includes --inexact."""
    def runner(cmd, **kwargs):  # noqa: ANN001
        if "--check" in cmd:
            return _fail()
        return _ok()

    engine_env.ensure_engine_env(app_dir, runner=runner)
    # Covered by test_heals_*; this pins the invariant explicitly.
    cmds = []

    def capture(cmd, **kwargs):  # noqa: ANN001
        cmds.append(list(cmd))
        return _fail() if "--check" in cmd else _ok()

    engine_env.ensure_engine_env(app_dir, runner=capture)
    assert all("--inexact" in c for c in cmds)


def test_missing_pyproject_is_noop_without_uv(tmp_path: Path) -> None:
    """Edge: no pyproject → noop/failed soft; runner never called."""
    bare = tmp_path / "bare"
    bare.mkdir()
    calls: list[list[str]] = []

    def runner(cmd, **kwargs):  # noqa: ANN001
        calls.append(list(cmd))
        return _ok()

    report = engine_env.ensure_engine_env(bare, runner=runner)
    assert report.action in {"noop", "failed"}
    assert calls == []
    assert report.reason


def test_uv_failure_is_soft_failed(app_dir: Path) -> None:
    """Edge: heal subprocess failure → action failed with reason, no raise."""
    def runner(cmd, **kwargs):  # noqa: ANN001
        if "--check" in cmd:
            return _fail()
        return _fail(stderr="network boom", code=2)

    report = engine_env.ensure_engine_env(app_dir, runner=runner)
    assert report.action == "failed"
    assert "boom" in report.reason or report.reason


def test_runner_timeout_is_soft_failed(app_dir: Path) -> None:
    """Edge: TimeoutExpired → failed soft."""
    def runner(cmd, **kwargs):  # noqa: ANN001
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=kwargs.get("timeout", 1))

    report = engine_env.ensure_engine_env(app_dir, runner=runner, timeout=1)
    assert report.action == "failed"
    assert report.reason
