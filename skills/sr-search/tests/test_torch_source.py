"""Tests for durable torch-index persistence and ensure_torch heal."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from stockroom import torch_source


@pytest.fixture
def stockroom_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / "stockroom-home"
    home.mkdir()
    monkeypatch.setenv("STOCKROOM_HOME", str(home))
    return home


@pytest.fixture
def app_dir(tmp_path: Path) -> Path:
    d = tmp_path / "engine"
    d.mkdir()
    (d / "pyproject.toml").write_text("[project]\nname='stockroom'\n")
    return d


def _ok() -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")


def _fail(stderr: str = "boom") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr=stderr)


def test_write_read_index_round_trip(stockroom_home: Path) -> None:
    """T1: recorded index survives under STOCKROOM_HOME."""
    url = "https://download.pytorch.org/whl/cu126"
    path = torch_source.write_index(url)
    assert path == stockroom_home / "torch-index"
    assert torch_source.read_index() == url


def test_read_index_none_when_missing(stockroom_home: Path) -> None:
    assert torch_source.read_index() is None


def test_write_index_rejects_non_https(stockroom_home: Path) -> None:
    with pytest.raises(ValueError, match="https://"):
        torch_source.write_index("http://example.com/whl")


def test_ensure_torch_noop_when_importable(app_dir: Path, stockroom_home: Path) -> None:
    """T2: torch already importable → noop; no pip."""
    calls: list[list[str]] = []

    def runner(cmd, **kwargs):  # noqa: ANN001
        calls.append(list(cmd))
        return _ok()

    # Pretend venv python exists so import check runs.
    py = app_dir / ".venv" / "bin" / "python"
    py.parent.mkdir(parents=True)
    py.write_text("#!/bin/sh\n")
    py.chmod(0o755)

    report = torch_source.ensure_torch(app_dir, runner=runner)
    assert report.action == "noop"
    assert calls and calls[0][-1] == "import torch"
    assert not any("pip" in c for c in calls)


def test_ensure_torch_installs_from_record(
    app_dir: Path, stockroom_home: Path
) -> None:
    """T3: missing torch + recorded index → uv pip install with that index."""
    url = "https://download.pytorch.org/whl/cpu"
    torch_source.write_index(url)
    py = app_dir / ".venv" / "bin" / "python"
    py.parent.mkdir(parents=True)
    py.write_text("#!/bin/sh\n")
    py.chmod(0o755)

    calls: list[list[str]] = []

    def runner(cmd, **kwargs):  # noqa: ANN001
        calls.append(list(cmd))
        if "import torch" in cmd:
            return _fail("No module named torch")
        return _ok()

    report = torch_source.ensure_torch(app_dir, runner=runner)
    assert report.action == "installed"
    pip = next(c for c in calls if "pip" in c)
    assert pip[:4] == ["uv", "pip", "install", "torch"]
    assert "--no-config" in pip
    assert "--directory" in pip
    assert str(app_dir) in pip or str(Path(os.path.abspath(app_dir))) in pip
    assert "--index" in pip
    assert url in pip


def test_ensure_torch_fails_without_record(
    app_dir: Path, stockroom_home: Path
) -> None:
    """T4: missing torch + no record → failed soft; no pip."""
    py = app_dir / ".venv" / "bin" / "python"
    py.parent.mkdir(parents=True)
    py.write_text("#!/bin/sh\n")
    py.chmod(0o755)

    calls: list[list[str]] = []

    def runner(cmd, **kwargs):  # noqa: ANN001
        calls.append(list(cmd))
        return _fail("No module named torch")

    report = torch_source.ensure_torch(app_dir, runner=runner)
    assert report.action == "failed"
    assert "sr-initialize" in report.reason or "record" in report.reason.lower()
    assert not any("pip" in c for c in calls)
