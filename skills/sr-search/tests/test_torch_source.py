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
    """Recorded index survives under STOCKROOM_HOME."""
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
    """Torch already importable → noop even if freeze present; no pip."""
    url = "https://download.pytorch.org/whl/cpu"
    freeze = stockroom_home / "torch-requirements.txt"
    freeze.write_text(
        f"--index-url {url}\ntorch==2.7.1+cpu \\\n    --hash=sha256:deadbeef\n",
        encoding="utf-8",
    )
    torch_source.write_index(url)
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


def test_ensure_torch_installs_from_freeze(app_dir: Path, stockroom_home: Path) -> None:
    """Missing torch + freeze present → --require-hashes -r freeze; no bare index install."""
    url = "https://download.pytorch.org/whl/cpu"
    freeze = stockroom_home / "torch-requirements.txt"
    freeze.write_text(
        f"--index-url {url}\ntorch==2.7.1+cpu \\\n    --hash=sha256:deadbeef\n",
        encoding="utf-8",
    )
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
    assert pip[:3] == ["uv", "pip", "install"]
    assert "--require-hashes" in pip
    assert "-r" in pip
    assert str(freeze) in pip
    assert "--no-config" in pip
    assert "--directory" in pip
    assert str(app_dir) in pip or str(Path(os.path.abspath(app_dir))) in pip
    # Must not floating-install torch by name with --index alone.
    assert not (
        pip[3] == "torch" and "--index" in pip and "--require-hashes" not in pip
    )


def test_ensure_torch_fails_without_freeze(app_dir: Path, stockroom_home: Path) -> None:
    """Missing torch + no freeze → failed soft; no pip (even if index sidecar exists)."""
    torch_source.write_index("https://download.pytorch.org/whl/cpu")
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
    assert report.reason == (
        "torch missing and no hashed freeze at "
        f"{torch_source.requirements_path()} — run sr-initialize (install → smoke → "
        "freeze) or see docs/user-guide/troubleshooting/torch.md"
    )
    assert not any("pip" in c for c in calls)


def test_ensure_torch_fails_on_corrupt_freeze(
    app_dir: Path, stockroom_home: Path
) -> None:
    """Edge: corrupt freeze (no hashes) → soft-fail; no pip."""
    (stockroom_home / "torch-requirements.txt").write_text(
        "torch==2.7.1+cpu\n", encoding="utf-8"
    )
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
    assert not any("pip" in c for c in calls)


def _venv_python(app_dir: Path) -> Path:
    py = app_dir / ".venv" / "bin" / "python"
    py.parent.mkdir(parents=True)
    py.write_text("#!/bin/sh\n")
    py.chmod(0o755)
    return py


def test_freeze_torch_writes_hashed_requirements(
    app_dir: Path, stockroom_home: Path
) -> None:
    """Importable torch + index → hashed requirements + torch-index sidecar."""
    url = "https://download.pytorch.org/whl/cpu"
    version = "2.7.1+cpu"
    _venv_python(app_dir)
    compiled = (
        f"--index-url {url}\n"
        f"torch=={version} \\\n"
        f"    --hash=sha256:deadbeef\n"
        f"filelock==3.16.1 \\\n"
        f"    --hash=sha256:cafebabe\n"
    )
    calls: list[tuple[list[str], dict]] = []

    def runner(cmd, **kwargs):  # noqa: ANN001
        calls.append((list(cmd), dict(kwargs)))
        if "import torch" in " ".join(cmd) and "print" in " ".join(cmd):
            return subprocess.CompletedProcess(
                args=cmd, returncode=0, stdout=version + "\n", stderr=""
            )
        if "compile" in cmd:
            out = Path(cmd[cmd.index("-o") + 1])
            out.write_text(compiled, encoding="utf-8")
            return _ok()
        return _ok()

    report = torch_source.freeze_torch(app_dir, url, runner=runner)
    assert report.action == "written"
    req = stockroom_home / "torch-requirements.txt"
    assert report.requirements_path == req
    text = req.read_text(encoding="utf-8")
    assert f"torch=={version}" in text
    assert "--hash=" in text
    assert url in text
    assert torch_source.read_index() == url
    compile_cmd = next(c for c, _ in calls if "compile" in c)
    assert compile_cmd[:3] == ["uv", "pip", "compile"]
    assert "--generate-hashes" in compile_cmd
    assert "--emit-index-url" in compile_cmd
    assert "--default-index" in compile_cmd
    assert url in compile_cmd
    assert "--no-config" in compile_cmd
    compile_kwargs = next(kw for c, kw in calls if "compile" in c)
    assert compile_kwargs.get("input") == f"torch=={version}\n"


def test_freeze_torch_refuses_without_torch(
    app_dir: Path, stockroom_home: Path
) -> None:
    """No importable torch → failed; no freeze file written."""
    url = "https://download.pytorch.org/whl/cpu"
    _venv_python(app_dir)
    calls: list[list[str]] = []

    def runner(cmd, **kwargs):  # noqa: ANN001
        calls.append(list(cmd))
        return _fail("No module named torch")

    report = torch_source.freeze_torch(app_dir, url, runner=runner)
    assert report.action == "failed"
    assert "torch" in report.reason.lower()
    assert not (stockroom_home / "torch-requirements.txt").exists()
    assert not any("compile" in c for c in calls)


def test_freeze_torch_soft_fails_on_compile_error(
    app_dir: Path, stockroom_home: Path
) -> None:
    """Edge: uv pip compile failure → soft-fail with reason; no freeze written."""
    url = "https://download.pytorch.org/whl/cpu"
    _venv_python(app_dir)

    def runner(cmd, **kwargs):  # noqa: ANN001
        joined = " ".join(cmd)
        if "import torch" in joined and "print" in joined:
            return subprocess.CompletedProcess(
                args=cmd, returncode=0, stdout="2.7.1+cpu\n", stderr=""
            )
        if "compile" in cmd:
            return _fail("compile boom")
        return _ok()

    report = torch_source.freeze_torch(app_dir, url, runner=runner)
    assert report.action == "failed"
    assert "compile boom" in report.reason or "compile" in report.reason.lower()
    assert not (stockroom_home / "torch-requirements.txt").exists()


def test_freeze_torch_soft_fails_on_compile_timeout(
    app_dir: Path, stockroom_home: Path
) -> None:
    """Edge: uv pip compile timeout → soft-fail with reason; no freeze written."""
    url = "https://download.pytorch.org/whl/cpu"
    _venv_python(app_dir)

    def runner(cmd, **kwargs):  # noqa: ANN001
        joined = " ".join(cmd)
        if "import torch" in joined and "print" in joined:
            return subprocess.CompletedProcess(
                args=cmd, returncode=0, stdout="2.7.1+cpu\n", stderr=""
            )
        if "compile" in cmd:
            raise subprocess.TimeoutExpired(cmd=cmd, timeout=1.0)
        return _ok()

    report = torch_source.freeze_torch(app_dir, url, runner=runner)
    assert report.action == "failed"
    assert report.reason == "uv pip compile timed out after 1.0s"
    assert not (stockroom_home / "torch-requirements.txt").exists()
